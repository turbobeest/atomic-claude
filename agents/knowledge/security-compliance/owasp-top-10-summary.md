# OWASP Top 10 - 2021 Summary

> **Source**: https://owasp.org/www-project-top-ten/
> **Extracted**: 2025-12-21
> **Refresh**: When OWASP Top 10 2025 releases (expected November 2025)

## The Top 10 Security Risks

### A01:2021 - Broken Access Control
- Moved from #5 to #1 (94% of applications tested)
- Access control enforces policy so users cannot act outside their intended permissions
- **Mitigations**: Deny by default, implement access control mechanisms once, minimize CORS usage

### A02:2021 - Cryptographic Failures
- Previously "Sensitive Data Exposure" - refocused on crypto root cause
- Failures related to cryptography leading to sensitive data exposure
- **Mitigations**: Classify data, don't store sensitive data unnecessarily, encrypt all data in transit

### A03:2021 - Injection
- Dropped from #1 to #3 (94% of apps tested for injection)
- SQL, NoSQL, OS command, LDAP injection
- **Mitigations**: Use parameterized queries, positive server-side input validation, escape special characters

### A04:2021 - Insecure Design
- New category for 2021 - focuses on design flaws vs implementation bugs
- Missing or ineffective security controls at design phase
- **Mitigations**: Threat modeling, secure design patterns, reference architectures

### A05:2021 - Security Misconfiguration
- Moved up from #6 (90% of apps tested)
- Insecure default configs, incomplete configs, open cloud storage
- **Mitigations**: Hardened, minimal platform, review and update configurations, automated verification

### A06:2021 - Vulnerable and Outdated Components
- Previously "Using Components with Known Vulnerabilities"
- Libraries, frameworks with known CVEs
- **Mitigations**: Remove unused dependencies, inventory versions, monitor CVE databases, obtain from official sources

### A07:2021 - Identification and Authentication Failures
- Previously "Broken Authentication" - dropped from #2
- Session management, credential stuffing, weak passwords
- **Mitigations**: MFA, no default credentials, password complexity, rate limiting

### A08:2021 - Software and Data Integrity Failures
- New category focusing on assumptions about software updates and CI/CD
- Insecure deserialization merged into this category
- **Mitigations**: Digital signatures, verify dependencies, review CI/CD pipeline security

### A09:2021 - Security Logging and Monitoring Failures
- Previously "Insufficient Logging & Monitoring"
- Inability to detect, escalate, respond to breaches
- **Mitigations**: Log all access control and input validation failures, ensure logs are in consumable format

### A10:2021 - Server-Side Request Forgery (SSRF)
- New in 2021, added from community survey
- Web app fetches remote resource without validating user-supplied URL
- **Mitigations**: Segment remote resource access, enforce URL schemas, disable HTTP redirections

## Quick Reference

| Rank | Category | CWE Mapped | Incidence Rate |
|------|----------|------------|----------------|
| A01 | Broken Access Control | 34 | 3.81% |
| A02 | Cryptographic Failures | 29 | 4.49% |
| A03 | Injection | 33 | 3.37% |
| A04 | Insecure Design | 40 | 3.00% |
| A05 | Security Misconfiguration | 20 | 4.51% |
| A06 | Vulnerable Components | 3 | 8.77% |
| A07 | Auth Failures | 22 | 2.55% |
| A08 | Integrity Failures | 10 | 2.05% |
| A09 | Logging Failures | 4 | 6.51% |
| A10 | SSRF | 1 | 2.72% |

---
*This excerpt was curated for agent knowledge grounding. See source URL for full context.*
