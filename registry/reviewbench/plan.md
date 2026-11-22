# ReviewBench: confirmatory run

Written on 2026-11-24, after the SWE-bench and Code Review Bench results were seen and before any
ReviewBench subject was reviewed. Its sample leaves out the pull requests eyeful's prompts were
developed on, so it tests whether the main results hold on others.

1. **Subjects.** The 50 pull requests below, drawn by `build.reviewbench` from the 219 in the
   benchmark's manifest less the 25 of its test set that eyeful was developed on, in SHA-256 order of
   their keys with each language's share of seats. They were drawn on 2026-11-21.
   Reviews were run on ReviewBench during development, before this sample was drawn, and which pull
   requests they covered is not recorded, so earlier exposure of some of these 50 cannot be ruled
   out; no record shows any of them read against its golden comments.
2. **Reviews.** The same build (`61c1b8b`), model, reasoning level, pi version and sandbox as the main
   runs; panel once, single three times, fixed once, each under execution, read_only and none, one
   review at a time.
3. **Scoring.** The benchmark's own judge through `score.reviewbench`, with the same model.
4. **Analysis.** `analysis.analyze`, as for the main results: the panel against the single agent's first run and its
   three runs (McNemar's exact test), precision by condition (paired bootstrap), and cost.
5. **Reporting.** Reported in full beside the main results, whatever they show. A result that differs
   from the main runs is reported as a difference, not used to replace them.

Planned for February 2027, as in the proposal's schedule. Any change before the first review is
recorded in `amendments.md`.

## Sample

- `ComposioHQ_agent-orchestrator_1277-76652c7c`
- `EdV4H_usketch_534-719aa834`
- `Hermione-Granger-1176_artifacts_24-5d880a71`
- `LittleAndi_FileHorizon_19-958f48b3`
- `Mirkiux_featkit_17-de0187b0`
- `SolidOS_solid-panes_598-38141b1f`
- `SpanPanel_span_207-212c534d`
- `Tzeusy_butlers_1021-403e15fe`
- `Tzeusy_butlers_990-d66a3fe8`
- `VeyronSakai_UniCortex_162-e74a1d69`
- `WhatIfWeDigDeeper_application-tracker_261-c1bdc879`
- `arolariu_arolariu.ro_615-ef4814f4`
- `biralavor_42_transcendence_115-928703e9`
- `blamechris_chroxy_2266-7febfc48`
- `cjolivier01_hm-cupano_14-03aa0246`
- `control-theory_gonzo_129-0b9dd56f`
- `davidortinau_SentenceStudio_72-8941b5da`
- `demaconsulting_BuildMark_137-74a4b88d`
- `dotnet_sdk_53693-e993b64d`
- `edercnj_ia-dev-environment_134-986305ff`
- `fredericboyer_dev-team_797-3bc9ea25`
- `heyitsaamir_teamscli_31-ec0e9d9a`
- `hoangsonww_Claude-Code-Agent-Monitor_58-cd6b385a`
- `hughdidit_DAISy-Agency_274-1c88a238`
- `hughdidit_DAISy-Agency_294-690f26b6`
- `joshjohanning_bulk-github-repo-settings-sync-action_120-7d62e090`
- `khanjal_gig-logger_430-f5e5bf9b`
- `kodrunhq_opencode-autopilot_86-3bb1ca09`
- `kutanti_litmusai_67-48e73983`
- `logos-blockchain_lez-programs_52-9f34384d`
- `ls1intum_Artemis_12479-237b3656`
- `mamu7211_feirb-mailclient_215-d15c6ca6`
- `mikecubed_m3OS_84-5e9d78eb`
- `namehash_ensnode_1938-73085b32`
- `navikt_k9-brukerdialog-prosessering_480-f828e2d8`
- `obot-platform_obot_6355-1414ee32`
- `pnpm_pnpm_11268-e4127110`
- `psalm_psalm-plugin-laravel_642-a867cca3`
- `rulecom_rule-io-sdk_35-9b3046d9`
- `saasquatch_program-tools_490-7a9aa6b4`
- `scorbo2_ext-sn-statistics_15-05bd0901`
- `shaypal5_pr-agent-context_75-7c51cc54`
- `sirosfoundation_go-wallet-backend_76-28ffb41a`
- `snb4crazy_ai_agent_laravel_backend_2-cbd7b532`
- `supa-magic_spm_19-c60d2e03`
- `swt-labs_vibe-better-with-claude-code-vbw_358-c6082353`
- `tableau_server-client-python_1760-c2c05c5f`
- `vndee_memex_6-e392a168`
- `vriesdemichael_keycloak-operator_696-4db0ddea`
- `wspulse_client-ts_20-2c7574bc`
