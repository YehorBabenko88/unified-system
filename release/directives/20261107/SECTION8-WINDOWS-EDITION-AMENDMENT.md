# Effective §8 amendment — Windows editions, 7 November 2026

Direct owner decision: release/decisions/windows-home-20261107/OWNER-DECISION.json. The original OWNER-CONTINUATION.txt remains unchanged as historical evidence. This amendment replaces the blanket Windows11Pro requirement in §8.

LS5, PC4 and PC3 retain coordinator roles. PC2 remains a Pro worker. PC1 and LS7 are separately qualified Windows11Home workers with Terminan capability; they are not admitted as coordinators without separate qualification and owner approval. No automatic edition upgrade or OS/security-policy change is authorized.

WINDOWS_PRO_QUALIFICATION and WINDOWS_HOME_QUALIFICATION are independent tracks. Each Home node must pass its own14 mandatory checks; no Pro/other-node PASS transfer. Source/model/WindowsServer CI results and read-only SSH observations do not qualify Home runtime. Any Home-incompatible feature requires a demonstrated alternative with equivalent guarantees or a specific BLOCKED state.

All remaining §8 native/runtime/security obligations are preserved. Both Home installation gates remain BLOCKED until their prerequisite evidence is independently accepted; other development and isolated testing continue. No Firewall/ESET/Tailscale changes or production operations are authorized.
