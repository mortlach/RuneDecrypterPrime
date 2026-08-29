# Liber Primus typed workflows

Public workflows use the `api.liber_primus` namespace:

```python
from rdp import api

document = api.liber_primus.load_main_transcript()
locator = api.liber_primus.FragmentLocator(
    page_ref=api.liber_primus.PageReference.canon_page(54)
)
payload = api.liber_primus.payload_from_locator(locator)
```

Solved-source work should prefer the stable label route:

```python
payload = api.liber_primus.payload_from_label("welcome_pilgrim")
```

Complete main pages are also available:

```python
payload = api.liber_primus.payload_from_main_pages(1, 2)
```

The resulting solver payload provides normalized ciphertext indices and
word-length information suitable for `api.RuneIndexInput`.

Registry mutation, partition construction and transcript maintenance are
contributor operations. Code that genuinely needs them imports the exact data
module that owns the capability; normal user guides and tutorials do not expose
those internals.
