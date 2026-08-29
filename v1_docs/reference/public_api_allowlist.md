# V1 Public API Allowlist

Status: implemented V1 contract

The definition-owning package is `src/rdp/api/`. Normal consumers use
`from rdp import api`. The table below is exhaustive: its 141 paths are the
32 root exports plus the 65 advanced, 22 display, 18 Liber Primus, and four
experimental exports. Importable implementation helpers not listed here are
internal.

| Import path | Stability | Notes |
| --- | --- | --- |
| `rdp.api.run` | Public V1 surface | Root operation. |
| `rdp.api.encrypt` | Public V1 surface | Root operation. |
| `rdp.api.decrypt` | Public V1 surface | Root operation. |
| `rdp.api.RunSpec` | Public V1 surface | Root request type. |
| `rdp.api.RunResult` | Public V1 surface | Root result type. |
| `rdp.api.CipherSpec` | Public V1 surface | Root specification type. |
| `rdp.api.KeySpec` | Public V1 surface | Root specification type. |
| `rdp.api.SolverSpec` | Public V1 surface | Root specification type. |
| `rdp.api.ScoringConfig` | Public V1 surface | Root configuration type. |
| `rdp.api.LoggingConfig` | Public V1 surface | Root configuration type. |
| `rdp.api.InterruptorConfig` | Public V1 surface | Root configuration type. |
| `rdp.api.RawTextInput` | Public V1 surface | Root input type. |
| `rdp.api.RuneIndexInput` | Public V1 surface | Root input type. |
| `rdp.api.SourceReferenceInput` | Public V1 surface | Root input type. |
| `rdp.api.ProblemInput` | Public V1 surface | Root type alias. |
| `rdp.api.ConcreteKey` | Public V1 surface | Root type alias. |
| `rdp.api.RuneIndices` | Public V1 surface | Root type alias. |
| `rdp.api.InitialKeys` | Public V1 surface | Root type alias. |
| `rdp.api.TextDirection` | Public V1 surface | Root enum. |
| `rdp.api.ComputeDevice` | Public V1 surface | Root enum. |
| `rdp.api.WordLengthPolicy` | Public V1 surface | Root enum. |
| `rdp.api.RunStatus` | Public V1 surface | Root status type. |
| `rdp.api.RdpError` | Public V1 surface | Root exception. |
| `rdp.api.ConfigurationError` | Public V1 surface | Root exception. |
| `rdp.api.CapabilityUnavailableError` | Public V1 surface | Root exception. |
| `rdp.api.AssetUnavailableError` | Public V1 surface | Root exception. |
| `rdp.api.NonInvertibleCipherError` | Public V1 surface | Root exception. |
| `rdp.api.ExecutionError` | Public V1 surface | Root exception. |
| `rdp.api.advanced` | Public V1 surface | Advanced namespace. |
| `rdp.api.display` | Public V1 surface | Display namespace. |
| `rdp.api.liber_primus` | Public V1 surface | Liber Primus namespace. |
| `rdp.api.experimental` | Public V1 surface | Experimental namespace. |
| `rdp.api.advanced.RunArtifactManifestRow` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ConfigurationResolution` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.OracleMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.OracleReport` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ReproducibilityMetadata` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.RunConfigurationReport` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SolverReport` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.StopReason` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ExecutionStatus` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.RecoveryStatus` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.StopCategory` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.CapabilityEffectiveState` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.CapabilityIssue` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.CapabilityRequestState` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.CapabilityStatus` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.CipherKeyMismatchError` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.CipherRegistrationError` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ComponentContract` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ComponentKind` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.FallbackPolicy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.InvalidConcreteKeyError` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.RankingEffect` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ReleaseStatus` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScorerCapabilityReport` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScoringLane` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScoringLaneStatus` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.UnknownComponentError` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.UnsupportedConfigurationError` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.HardCribConfig` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.HardCribMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScoringObjective` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.HammingDictionaryPolicy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.AverageWindowPolicy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.BeamExpansionMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.CipherKind` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.InterruptorSearchStrategy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.KeyKind` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.FloatDType` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.HammingTextDirectionMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.IndexPermutation` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.InterruptorMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.JsonObject` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.JsonPrimitive` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.JsonValue` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.KaedingBlockSchedule` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.KaedingSlipPolicy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.LanguageModelBoundaryMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.OutOfVocabularyPolicy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.PeriodicColumnarOrder` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ProgressCallback` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScheduledStreamOperation` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScheduledStreamSchedule` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScoreDirection` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScoreStatistic` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScorerBackend` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScoringObjectiveKind` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SmoothingMethod` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SolverKind` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SpanHammingBucketPolicy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SpanHammingCombineMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SpanHammingGateFailurePolicy` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SpanHammingLanguageModelProfileSource` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.SpanHammingMode` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.WordLengthInfo` | Public V1 surface | Advanced export. |
| `rdp.api.advanced.ScorerReport` | Public V1 surface | Advanced export. |
| `rdp.api.display.SUMMARY_RELATIVE_PATH` | Public V1 surface | Display export. |
| `rdp.api.display.SUMMARY_SCHEMA` | Public V1 surface | Display export. |
| `rdp.api.display.SummaryOptions` | Public V1 surface | Display export. |
| `rdp.api.display.DisplaySummary` | Public V1 surface | Display export. |
| `rdp.api.display.BannerStyle` | Public V1 surface | Display export. |
| `rdp.api.display.PrintDetail` | Public V1 surface | Display export. |
| `rdp.api.display.PrintFormat` | Public V1 surface | Display export. |
| `rdp.api.display.PrintOptions` | Public V1 surface | Display export. |
| `rdp.api.display.build_summary` | Public V1 surface | Display export. |
| `rdp.api.display.format_summary` | Public V1 surface | Display export. |
| `rdp.api.display.print_summary` | Public V1 surface | Display export. |
| `rdp.api.display.render_summary` | Public V1 surface | Display export. |
| `rdp.api.display.print_result` | Public V1 surface | Display export. |
| `rdp.api.display.write_summary_json` | Public V1 surface | Display export. |
| `rdp.api.display.write_summary_artifact` | Public V1 surface | Display export. |
| `rdp.api.display.format_banner` | Public V1 surface | Display export. |
| `rdp.api.display.format_key_value_block` | Public V1 surface | Display export. |
| `rdp.api.display.format_preview_block` | Public V1 surface | Display export. |
| `rdp.api.display.format_section` | Public V1 surface | Display export. |
| `rdp.api.display.format_status_block` | Public V1 surface | Display export. |
| `rdp.api.display.print_block` | Public V1 surface | Display export. |
| `rdp.api.display.print_text` | Public V1 surface | Display export. |
| `rdp.api.liber_primus.Section` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.SolverPayload` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.FragmentLocator` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.LineReadMode` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.LineRuneSelector` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.SpiralRoute` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.PartitionEntry` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.PageReference` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.Transcript` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.get_section` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.payload_from_label` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.payload_from_locator` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.payload_from_main_pages` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.payload_from_partition_entry` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.load_main_section_indices` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.load_main_transcript` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.load_section_indices` | Public V1 surface | Liber Primus export. |
| `rdp.api.liber_primus.load_section_inputs` | Public V1 surface | Liber Primus export. |
| `rdp.api.experimental.DegeneracyPolicy` | Public V1 surface | Experimental export. |
| `rdp.api.experimental.ResolverMode` | Public V1 surface | Experimental export. |
| `rdp.api.experimental.define_cipher_lookup` | Public V1 surface | Experimental export. |
| `rdp.api.experimental.define_cipher_map` | Public V1 surface | Experimental export. |

There is no compatibility namespace, runtime cipher instance, generic
transform operation, or automatic internal fallback in V1.
