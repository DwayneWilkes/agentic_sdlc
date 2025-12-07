# Technical Debt Log

This log tracks quality gate exceptions that were approved but need future remediation.

## Open Items

### TD-5.1-20251205 - Coverage Gap in NATS Bus

- **Phase:** 5.1 - Inter-Agent Communication Protocol
- **Gate:** Coverage
- **Current:** 54% | **Required:** 80%
- **Approved By:** (initial development)
- **Approved Date:** 2025-12-05
- **Reason:** Core functionality works, edge cases not yet tested
- **Target Remediation:** TBD
- **Status:** 🟡 Open

### TD-5.2-20251205 - Coverage Gap in Coordination

- **Phase:** 5.2 - Shared State and Context Manager
- **Gate:** Coverage
- **Current:** 44% | **Required:** 80%
- **Approved By:** (initial development)
- **Approved Date:** 2025-12-05
- **Reason:** Core functionality works, edge cases not yet tested
- **Target Remediation:** TBD
- **Status:** 🟡 Open

### TD-1.3-20251205 - Coverage Gap in Task Decomposer

- **Phase:** 1.3 - Task Decomposition Engine
- **Gate:** Coverage
- **Current:** 74% | **Required:** 80%
- **Approved By:** (initial development)
- **Approved Date:** 2025-12-05
- **Reason:** Core functionality works, 6% gap
- **Target Remediation:** TBD
- **Status:** 🟡 Open

## Resolved Items

(None yet)

---

## Process

1. Tech Lead identifies violations during phase audit
2. PM reviews and decides: remediate or approve exception
3. If exception approved, Tech Lead logs here with:
   - Phase reference
   - Specific gate and gap
   - Reason for approval
   - Target remediation date
4. Remediation agent fixes the gap
5. Tech Lead verifies fix and moves item to Resolved
