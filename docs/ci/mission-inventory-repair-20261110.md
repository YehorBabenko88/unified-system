# Mission Controller mandatory inventory repair

Original run 42869185791, source e869d8365c7e54ed3da3739d9cdf15948f37f022, failed on Ubuntu job130015537081 and Windows job130015537660 before executing fixture tests. The inline qualifier expected 47 IDs while discovery found 58. The missing cases were ten continuation regressions and the existing owned-temp-alias regression. This is a CI configuration defect, not an established application failure.

Original decoded logs retained outside source, SHA256:

- Ubuntu: 4e13f3ca7634cfc346f68f196c6b79cf8d59e7b42b48a7897ba2636a7753d845.
- Windows: 8c2aa587dd15c4e7f25c0080a61f878694632fbe8d7111a6cbdda6d8b7c8e352.

The repaired qualifier preserves all original 47 IDs and adds the missing eleven. A static regression freezes the original sorted-list encoding SHA256 5b18c7e3128d1810aa67a66730732265ec66daff410aa7baa20553aa5bf75495. Before fixture execution the predicate now rejects duplicate expected IDs as well as missing, extra or duplicate discovered IDs. No fixture assertion, timeout, source integrity or admission gate is removed.

Three initial static regressions reproduced two failures: omitted current cases and duplicate expected IDs accepted by the old pre-execution predicate. Original RED log SHA256 6e0fe64c278f09641cfd75e859b4c65c3bccf83bec2079868b06d337935480f0. Four final static guards pass; GREEN log SHA256 3026ec44bc7e8defaa63d1647f3f92526bd7ac348fd584f5641c783c93dd82de. They parse source and the actual workflow admission expression without importing fixture modules.

ROOT also executed the complete local 50 Mission Controller + 8 Journal + 4 static guards: 62 cases, zero failures/errors/skips, checked source bytes unchanged and no remaining Python threads. These tests use owned temporary SQLite and existing bounded child-process cases. They do not establish Codex app restart, autonomous dispatch, native authority, hosted qualification or physical admission. Exact-source hosted successor results remain pending; do not relabel the original failed run.
