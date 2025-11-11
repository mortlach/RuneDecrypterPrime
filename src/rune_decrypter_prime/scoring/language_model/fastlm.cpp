// ============================================================
// rune_decrypter_prime/scoring/language_model/fastlm.cpp   (pybind11 fast LM)
// Portable single-file C++ extension providing a hashed n-gram/WLI scorer.
// No behaviour changes; API consumed by language_model_prime.py as _fastlm.
// ============================================================

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <cstdint>
#include <stdexcept>
#include <cmath>
#include <vector>
#include <algorithm>
#include <cstring>

namespace py = pybind11;

// ───────────── Contiguity helpers (derive from strides) ─────────────
static inline bool is_c_contig_1d(const py::buffer_info& b) {
    return b.ndim == 1 && b.strides[0] == (py::ssize_t)b.itemsize;
}
static inline bool is_c_contig_2d(const py::buffer_info& b) {
    return b.ndim == 2
        && b.strides[1] == (py::ssize_t)b.itemsize
        && b.strides[0] == (py::ssize_t)(b.itemsize * b.shape[1]);
}
static inline bool is_c_contig_3d(const py::buffer_info& b) {
    return b.ndim == 3
        && b.strides[2] == (py::ssize_t)b.itemsize
        && b.strides[1] == (py::ssize_t)(b.itemsize * b.shape[2])
        && b.strides[0] == (py::ssize_t)(b.itemsize * b.shape[1] * b.shape[2]);
}

// ───── Minimal XXH64 (unaligned-safe with memcpy) ─────
static inline uint64_t XXH_rotl64(uint64_t x, int r){ return (x<<r)|(x>>(64-r)); }
static inline uint64_t rd64(const uint8_t* p){ uint64_t v; std::memcpy(&v,p,8); return v; }
static inline uint32_t rd32(const uint8_t* p){ uint32_t v; std::memcpy(&v,p,4); return v; }
static const uint64_t PRIME1=11400714785074694791ULL, PRIME2=14029467366897019727ULL,
                     PRIME3=1609587929392839161ULL,   PRIME4=9650029242287828579ULL,
                     PRIME5=2870177450012600261ULL;
static uint64_t XXH64(const void* input, size_t len, uint64_t seed){
    const uint8_t* p=(const uint8_t*)input; const uint8_t* bEnd=p+len; uint64_t h64;
    if(len>=32){
        const uint8_t* const limit=bEnd-32;
        uint64_t v1=seed+PRIME1+PRIME2, v2=seed+PRIME2, v3=seed+0, v4=seed-PRIME1;
        do{
            v1=XXH_rotl64(v1+rd64(p)*PRIME2,31)*PRIME1; p+=8;
            v2=XXH_rotl64(v2+rd64(p)*PRIME2,31)*PRIME1; p+=8;
            v3=XXH_rotl64(v3+rd64(p)*PRIME2,31)*PRIME1; p+=8;
            v4=XXH_rotl64(v4+rd64(p)*PRIME2,31)*PRIME1; p+=8;
        } while(p<=limit);
        h64 =  XXH_rotl64(v1,1) + XXH_rotl64(v2,7) + XXH_rotl64(v3,12) + XXH_rotl64(v4,18);
        auto MERGE=[&](uint64_t v){ v*=PRIME2; v=XXH_rotl64(v,31); v*=PRIME1; h64^=v; h64=h64*PRIME1+PRIME4; };
        MERGE(v1); MERGE(v2); MERGE(v3); MERGE(v4);
    } else { h64 = seed + PRIME5; }
    h64 += (uint64_t)len;
    while(p+8<=bEnd){ uint64_t k1=rd64(p)*PRIME2; p+=8; k1=XXH_rotl64(k1,31)*PRIME1; h64^=k1; h64=XXH_rotl64(h64,27)*PRIME1+PRIME4; }
    if(p+4<=bEnd){ h64^=(uint64_t)rd32(p)*PRIME1; p+=4; h64=XXH_rotl64(h64,23)*PRIME2+PRIME3; }
    while(p<bEnd){ h64^=(uint64_t)(*p++)*PRIME5; h64=XXH_rotl64(h64,11)*PRIME1; }
    h64^=h64>>33; h64*=PRIME2; h64^=h64>>29; h64*=PRIME3; h64^=h64>>32; return h64;
}
// ─────────────────────────────────────────────────────

enum class SmoothMode : int { None=0, Lidstone=1, Jeffreys=2, AutoGT=3 };
enum class OOVMode    : int { FloorMinSeen=0, Lidstone=1 };

class FastTransitionModel {
public:
    // Own arrays (kept alive via py::array)
    py::array_t<uint64_t> keys_arr;
    py::array_t<float>    logp_arr;   // overwritten with smoothed values
    py::array_t<uint64_t> cnts_arr;

    // Raw pointers
    const uint64_t *keys_ptr{nullptr};
    float          *logp_ptr{nullptr};
    const uint64_t *cnts_ptr{nullptr};

    // Hash table params
    uint32_t mask{0};
    size_t   N{0};

    // Stats for normalization (after smoothing)
    float    mu{0.0f}, sigma{1.0f};
    float    median{0.0f}, mad{1.0f}, mad_sigma{1.0f}; // mad_sigma = 1.4826 * MAD
    float    fallback_logp{-50.0f};  // OOV floor

    // Counts summary
    uint64_t T{0};
    uint32_t K{0};
    uint32_t N1{0};

    // Smoothing / OOV
    SmoothMode smooth{SmoothMode::None};
    OOVMode    oov{OOVMode::FloorMinSeen};
    float      alpha{0.0f};

    FastTransitionModel(
        py::array_t<uint64_t> keys_,
        py::array_t<float>    logp_,      // ignored on input; recomputed from counts+α
        py::array_t<uint64_t> cnts_,
        uint32_t              mask_,      // 2^lg - 1
        int                   smooth_mode,// 0=None,1=Lidstone,2=Jeffreys,3=AutoGT
        float                 lidstone_alpha, // used when Lidstone
        int                   oov_mode,   // 0=FloorMinSeen,1=Lidstone
        bool                  /*use_gpu*/ = false
    )
    : keys_arr(keys_), logp_arr(logp_), cnts_arr(cnts_), mask(mask_)
    {
        // ---- shape/dtype checks & pointers ----
        auto kbuf = keys_arr.request();
        if (kbuf.itemsize != sizeof(uint64_t) || !is_c_contig_1d(kbuf))
            throw std::runtime_error("keys must be 1D uint64 C-contiguous");
        N = static_cast<size_t>(kbuf.shape[0]);
        keys_ptr = static_cast<const uint64_t*>(kbuf.ptr);

        auto lpbuf = logp_arr.request();
        if (lpbuf.itemsize != sizeof(float) || !is_c_contig_1d(lpbuf)
            || static_cast<size_t>(lpbuf.shape[0]) != N)
            throw std::runtime_error("logp must be 1D float32 C-contiguous and match keys length");
        logp_ptr = static_cast<float*>(lpbuf.ptr); // will be overwritten with smoothed values

        auto cbuf = cnts_arr.request();
        if (cbuf.itemsize != sizeof(uint64_t) || !is_c_contig_1d(cbuf)
            || static_cast<size_t>(cbuf.shape[0]) != N)
            throw std::runtime_error("cnts must be 1D uint64 C-contiguous and match keys length");
        cnts_ptr = static_cast<const uint64_t*>(cbuf.ptr);

        // ---- derive counts stats ----
        T = 0; K = 0; N1 = 0;
        for (size_t i=0;i<N;++i) {
            uint64_t c = cnts_ptr[i];
            if (c) { T += c; K += 1; if (c==1) N1 += 1; }
        }

        // ---- resolve smoothing / OOV ----
        smooth = static_cast<SmoothMode>(smooth_mode);
        oov    = static_cast<OOVMode>(oov_mode);
        switch (smooth) {
            case SmoothMode::None:     alpha = 0.0f;           break;
            case SmoothMode::Lidstone: alpha = lidstone_alpha; break;
            case SmoothMode::Jeffreys: alpha = 0.5f;           break;
            case SmoothMode::AutoGT:
                alpha = (K > N1 && N1 > 0) ? float(N1) / float(K - N1) : 0.5f;
                break;
        }

        // ---- recompute logp from counts + α; compute mu/sigma + median/MAD; floor ----
        const float Veff = float(K > 0 ? K : 1);
        const float denom_log = std::log(float(T) + alpha * Veff);

        double sum=0.0, sum2=0.0; uint32_t obs=0;
        bool first=true; float min_lp=0.0f;
        std::vector<float> lps; lps.reserve(K);

        for (size_t i=0;i<N;++i) {
            uint64_t c = cnts_ptr[i];
            if (!c) { logp_ptr[i] = 0.0f; continue; }  // empty slot; never probed
            float lp = std::log(float(c) + alpha) - denom_log;
            logp_ptr[i] = lp;
            if (first || lp < min_lp) { min_lp = lp; first = false; }
            sum += lp; sum2 += lp*lp; obs++;
            lps.push_back(lp);
        }
        if (obs == 0) {
            mu = 0.0f; sigma = 1.0f; fallback_logp = -50.0f;
            median = 0.0f; mad = 1.0f; mad_sigma = 1.0f;
        } else {
            // mean/sd
            mu = float(sum / obs);
            double var = (sum2 / obs) - double(mu)*double(mu);
            sigma = float(std::sqrt(var > 1e-12 ? var : 1e-12));
            // OOV floor
            fallback_logp = (oov == OOVMode::FloorMinSeen)
                ? min_lp
                : (std::log(alpha) - denom_log);
            // robust stats: median & MAD
            std::nth_element(lps.begin(), lps.begin() + lps.size()/2, lps.end());
            median = lps[lps.size()/2];
            // absolute deviations
            for (float& v : lps) v = std::fabs(v - median);
            std::nth_element(lps.begin(), lps.begin() + lps.size()/2, lps.end());
            mad = lps[lps.size()/2];
            mad_sigma = std::max(1.4826f * mad, 1e-6f); // robust σ; guard tiny
        }
    }

    // ---- core probe (returns count + smoothed logp) ----
    inline void probe(uint64_t key, uint64_t& out_count, float& out_logp) const {
        uint32_t idx = static_cast<uint32_t>(key) & mask;
        while (true) {
            uint64_t k = keys_ptr[idx];
            if (k == 0ULL) { out_count=0; out_logp=fallback_logp; return; }
            if (k == key)  {
                uint64_t c = cnts_ptr[idx];
                if (c==0ULL){ out_count=0; out_logp=fallback_logp; return; }
                out_count = c;
                out_logp = logp_ptr[idx]; // smoothed
                return;
            }
            idx = (idx + 1) & mask;
        }
    }

    // ---------------- WLI (needs plaintexts N×L and wli N×L×2) ----------------
    // Token encoding: 5 bits rune (0..31), 6 bits pos, 6 bits len -> packed into uint32.
    py::array_t<float> batch_logp(py::array_t<uint8_t> plaintexts,
                                  py::array_t<uint8_t> wli,
                                  int n, int m){
        auto p_buf = plaintexts.request(), w_buf = wli.request();
        if (!is_c_contig_2d(p_buf) || !is_c_contig_3d(w_buf))
            throw std::runtime_error("plaintexts (N,L) and wli (N,L,2) must be C-contiguous");
        const py::ssize_t Np = p_buf.shape[0], L = p_buf.shape[1];
        const uint8_t* p = static_cast<uint8_t*>(p_buf.ptr);
        const uint8_t* w = static_cast<uint8_t*>(w_buf.ptr);

        py::array_t<float> out({Np});
        auto o_buf = out.request(); float* o = static_cast<float*>(o_buf.ptr);

        for (py::ssize_t i=0;i<Np;++i){
            float sum = 0.0f;
            for (py::ssize_t j=0; j + n + m <= L; ++j){
                uint32_t tokens[32]; int t=0;
                for (int k=0;k<n+m;++k){
                    uint8_t rune = p[i*L + j+k];
                    const uint8_t* wptr = &w[(i*L + j+k)*2];
                    uint8_t pos=wptr[0], len=wptr[1];
                    tokens[t++] = (uint32_t(rune & 0x1F) | (uint32_t(pos & 0x3F)<<5) | (uint32_t(len & 0x3F)<<11));
                }
                uint64_t key = XXH64(tokens, sizeof(uint32_t)*t, 0);
                uint64_t c; float lp; probe(key, c, lp); sum += lp;
            }
            o[i] = sum;
        }
        return out;
    }

    py::array_t<uint64_t> batch_count(py::array_t<uint8_t> plaintexts,
                                      py::array_t<uint8_t> wli,
                                      int n, int m){
        auto p_buf = plaintexts.request(), w_buf = wli.request();
        if (!is_c_contig_2d(p_buf) || !is_c_contig_3d(w_buf))
            throw std::runtime_error("plaintexts (N,L) and wli (N,L,2) must be C-contiguous");
        const py::ssize_t Np = p_buf.shape[0], L = p_buf.shape[1];
        const uint8_t* p = static_cast<uint8_t*>(p_buf.ptr);
        const uint8_t* w = static_cast<uint8_t*>(w_buf.ptr);

        py::array_t<uint64_t> out({Np});
        auto o_buf = out.request(); uint64_t* o = static_cast<uint64_t*>(o_buf.ptr);

        for (py::ssize_t i=0;i<Np;++i){
            uint64_t sum = 0;
            for (py::ssize_t j=0; j + n + m <= L; ++j){
                uint32_t tokens[32]; int t=0;
                for (int k=0;k<n+m;++k){
                    uint8_t rune = p[i*L + j+k];
                    const uint8_t* wptr = &w[(i*L + j+k)*2];
                    uint8_t pos=wptr[0], len=wptr[1];
                    tokens[t++] = (uint32_t(rune & 0x1F) | (uint32_t(pos & 0x3F)<<5) | (uint32_t(len & 0x3F)<<11));
                }
                uint64_t key = XXH64(tokens, sizeof(uint32_t)*t, 0);
                uint64_t c; float lp; (void)lp; probe(key, c, lp);
                sum += c;
            }
            o[i] = sum;
        }
        return out;
    }

    // Σ z_i = Σ ((lp_i − μ)/σ)    (no √W)
    py::array_t<float> batch_zsum(py::array_t<uint8_t> plaintexts,
                                  py::array_t<uint8_t> wli,
                                  int n, int m){
        py::array_t<float> raw = this->batch_logp(plaintexts, wli, n, m);
        auto rb = raw.request(); const float* r = static_cast<const float*>(rb.ptr);
        const py::ssize_t Np = rb.shape[0];

        auto pbuf = plaintexts.request();
        const float W = float(pbuf.shape[1] - (n + m) + 1);
        const float denom = (sigma > 1e-12f ? sigma : 1e-12f);

        py::array_t<float> out({Np}); auto ob = out.request(); float* o = static_cast<float*>(ob.ptr);
        for (py::ssize_t i=0;i<Np;++i){
            o[i] = (r[i] - W*mu) / denom;
        }
        return out;
    }

    // Σ mad_i = Σ ((lp_i − median) / (1.4826·MAD))
    py::array_t<float> batch_madsum(py::array_t<uint8_t> plaintexts,
                                    py::array_t<uint8_t> wli,
                                    int n, int m){
        py::array_t<float> raw = this->batch_logp(plaintexts, wli, n, m);
        auto rb = raw.request(); const float* r = static_cast<const float*>(rb.ptr);
        const py::ssize_t Np = rb.shape[0];

        auto pbuf = plaintexts.request();
        const float W = float(pbuf.shape[1] - (n + m) + 1);
        const float denom = (mad_sigma > 1e-12f ? mad_sigma : 1e-12f);

        py::array_t<float> out({Np}); auto ob = out.request(); float* o = static_cast<float*>(ob.ptr);
        for (py::ssize_t i=0;i<Np;++i){
            // Σ((lp − median)/(1.4826·MAD)) = ((Σlp) − W·median)/mad_sigma
            o[i] = (r[i] - W*median) / denom;
        }
        return out;
    }

    // ---------------- CHAR (no WLI; pos=len=0) ----------------
    py::array_t<float> batch_logp_char(py::array_t<uint8_t> plaintexts, int n){
        auto p_buf = plaintexts.request();
        if (!is_c_contig_2d(p_buf)) throw std::runtime_error("plaintexts (N,L) uint8 C-contiguous");
        const py::ssize_t Np=p_buf.shape[0], L=p_buf.shape[1];
        const uint8_t* p = static_cast<uint8_t*>(p_buf.ptr);

        py::array_t<float> out({Np}); auto o_buf=out.request(); float* o=static_cast<float*>(o_buf.ptr);
        for (py::ssize_t i=0;i<Np;++i){
            float sum=0.0f;
            for (py::ssize_t j=0;j + n <= L;++j){
                uint32_t tokens[32];
                for (int k=0;k<n;++k) tokens[k] = (uint32_t(p[i*L + j+k] & 0x1F)); // pos=len=0
                uint64_t key = XXH64(tokens, sizeof(uint32_t)*n, 0);
                uint64_t c; float lp; probe(key, c, lp); sum += lp;
            }
            o[i]=sum;
        }
        return out;
    }

    py::array_t<uint64_t> batch_count_char(py::array_t<uint8_t> plaintexts, int n){
        auto p_buf = plaintexts.request();
        if (!is_c_contig_2d(p_buf)) throw std::runtime_error("plaintexts (N,L) uint8 C-contiguous");
        const py::ssize_t Np=p_buf.shape[0], L=p_buf.shape[1];
        const uint8_t* p = static_cast<uint8_t*>(p_buf.ptr);

        py::array_t<uint64_t> out({Np}); auto o_buf=out.request(); uint64_t* o=static_cast<uint64_t*>(o_buf.ptr);
        for (py::ssize_t i=0;i<Np;++i){
            uint64_t sum=0;
            for (py::ssize_t j=0;j + n <= L;++j){
                uint32_t tokens[32];
                for (int k=0;k<n;++k) tokens[k] = (uint32_t(p[i*L + j+k] & 0x1F));
                uint64_t key=XXH64(tokens, sizeof(uint32_t)*n, 0);
                uint64_t c; float lp; probe(key,c,lp); sum+=c;
            }
            o[i]=sum;
        }
        return out;
    }

    py::array_t<float> batch_zsum_char(py::array_t<uint8_t> plaintexts, int n){
        py::array_t<float> raw = this->batch_logp_char(plaintexts, n);
        auto rb = raw.request(); const float* r = static_cast<const float*>(rb.ptr);
        const py::ssize_t Np = rb.shape[0];
        auto pbuf = plaintexts.request();
        const float W = float(pbuf.shape[1] - n + 1);
        const float denom = (sigma > 1e-12f ? sigma : 1e-12f);

        py::array_t<float> out({Np}); auto ob=out.request(); float* o=static_cast<float*>(ob.ptr);
        for (py::ssize_t i=0;i<Np;++i){
            o[i] = (r[i] - W*mu) / denom;
        }
        return out;
    }

    py::array_t<float> batch_madsum_char(py::array_t<uint8_t> plaintexts, int n){
        py::array_t<float> raw = this->batch_logp_char(plaintexts, n);
        auto rb = raw.request(); const float* r = static_cast<const float*>(rb.ptr);
        const py::ssize_t Np = rb.shape[0];
        auto pbuf = plaintexts.request();
        const float W = float(pbuf.shape[1] - n + 1);
        const float denom = (mad_sigma > 1e-12f ? mad_sigma : 1e-12f);

        py::array_t<float> out({Np}); auto ob=out.request(); float* o=static_cast<float*>(ob.ptr);
        for (py::ssize_t i=0;i<Np;++i){
            o[i] = (r[i] - W*median) / denom;
        }
        return out;
    }
};

PYBIND11_MODULE(_fastlm, m) {
    py::class_<FastTransitionModel>(m, "FastTransitionModel")
        .def(py::init<
             py::array_t<uint64_t>,
             py::array_t<float>,
             py::array_t<uint64_t>,
             uint32_t,
             int, float, int, bool>(),
             py::arg("keys"), py::arg("logp"), py::arg("cnts"),
             py::arg("mask"),
             py::arg("smooth_mode")   = 0,     // 0=None,1=Lidstone,2=Jeffreys,3=AutoGT
             py::arg("alpha")         = 1.0f,  // used if smooth_mode==1
             py::arg("oov_mode")      = 0,     // 0=FloorMinSeen,1=Lidstone
             py::arg("use_gpu")       = false)
        .def_readonly("mu",        &FastTransitionModel::mu)
        .def_readonly("sigma",     &FastTransitionModel::sigma)
        .def_readonly("median",    &FastTransitionModel::median)
        .def_readonly("mad",       &FastTransitionModel::mad)
        .def_readonly("mad_sigma", &FastTransitionModel::mad_sigma)
        .def_readonly("alpha",     &FastTransitionModel::alpha)
        .def_readonly("fallback_logp", &FastTransitionModel::fallback_logp)

        // WLI
        .def("batch_logp",   &FastTransitionModel::batch_logp,   py::arg("plaintexts"), py::arg("wli"), py::arg("n"), py::arg("m")=0)
        .def("batch_count",  &FastTransitionModel::batch_count,  py::arg("plaintexts"), py::arg("wli"), py::arg("n"), py::arg("m")=0)
        .def("batch_zsum",   &FastTransitionModel::batch_zsum,   py::arg("plaintexts"), py::arg("wli"), py::arg("n"), py::arg("m")=0)
        .def("batch_madsum", &FastTransitionModel::batch_madsum, py::arg("plaintexts"), py::arg("wli"), py::arg("n"), py::arg("m")=0)

        // CHAR
        .def("batch_logp_char",   &FastTransitionModel::batch_logp_char,   py::arg("plaintexts"), py::arg("n"))
        .def("batch_count_char",  &FastTransitionModel::batch_count_char,  py::arg("plaintexts"), py::arg("n"))
        .def("batch_zsum_char",   &FastTransitionModel::batch_zsum_char,   py::arg("plaintexts"), py::arg("n"))
        .def("batch_madsum_char", &FastTransitionModel::batch_madsum_char, py::arg("plaintexts"), py::arg("n"));
}

// TODO(perf): Consider SIMD for inner loops and/or a parallel variant for large N.
// TODO(cuda): Plumb a real GPU fast-path (use_gpu currently unused).
