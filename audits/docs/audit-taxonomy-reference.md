# SDLC Audit Taxonomy - Master Reference

A comprehensive taxonomy of audit domains, standards, and frameworks for Software Development Life Cycle audits.

## Overview

This document defines ALL audit dimensions that can be applied across any SDLC phase. Each dimension references authoritative standards and provides specific audit items.

---

## DOMAIN 1: REQUIREMENTS (REQ)

**Purpose**: Ensure requirements are complete, clear, testable, and traceable.

### Standards & Frameworks
- IEEE 830 (Software Requirements Specification)
- ISO/IEC/IEEE 29148 (Requirements Engineering)
- IREB (International Requirements Engineering Board)

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| REQ-001 | Requirements Completeness | Critical | All functional requirements documented |
| REQ-002 | Requirements Clarity | High | Unambiguous, single interpretation |
| REQ-003 | Acceptance Criteria Defined | Critical | Each requirement has testable acceptance criteria |
| REQ-004 | Requirements Traceability | High | Requirements traced to source and implementation |
| REQ-005 | Non-Functional Requirements | High | NFRs (performance, security, etc.) specified |
| REQ-006 | User Stories Quality | Medium | INVEST criteria met (Independent, Negotiable, etc.) |
| REQ-007 | Edge Cases Identified | High | Boundary conditions and error scenarios documented |
| REQ-008 | Dependencies Documented | Medium | External dependencies and assumptions explicit |
| REQ-009 | Priority Assignment | Medium | Requirements prioritized (MoSCoW, etc.) |
| REQ-010 | Stakeholder Sign-off | High | Requirements approved by stakeholders |
| REQ-011 | Scope Boundaries | High | In-scope and out-of-scope clearly defined |
| REQ-012 | Glossary/Terminology | Medium | Domain terms defined consistently |
| REQ-013 | Constraints Documented | Medium | Technical, business, regulatory constraints listed |
| REQ-014 | Success Metrics | High | KPIs and success criteria defined |
| REQ-015 | Change Management | Medium | Process for requirement changes defined |

---

## DOMAIN 2: SECURITY (SEC)

**Purpose**: Ensure software is secure by design and implementation.

### Standards & Frameworks
- **OWASP ASVS 5.0** - Application Security Verification Standard (350 requirements)
- **OWASP MASVS** - Mobile Application Security Verification Standard
- **OWASP Top 10** - Critical web application security risks
- **NIST SP 800-53** - Security and Privacy Controls
- **NIST SP 800-218 (SSDF)** - Secure Software Development Framework
- **CIS Controls v8** - Center for Internet Security Controls
- **SANS Top 25** - Most Dangerous Software Weaknesses
- **ISO 27001** - Information Security Management
- **NSA Zero Trust Guidance** - Zero trust architecture implementation
- **Microsoft SDL** - Security Development Lifecycle

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| SEC-001 | Authentication Mechanisms | Critical | Auth method specified (OAuth, JWT, session) |
| SEC-002 | Authorization Model | Critical | RBAC/ABAC, permission matrix defined |
| SEC-003 | Data Encryption | Critical | TLS, at-rest encryption, key management |
| SEC-004 | Input Validation | Critical | Sanitization, injection prevention |
| SEC-005 | OWASP Top 10 | Critical | All OWASP Top 10 risks addressed |
| SEC-006 | Secrets Management | High | No hardcoded secrets, vault usage |
| SEC-007 | Audit Logging | High | Security events logged, tamper-proof |
| SEC-008 | API Security | High | Rate limiting, CORS, API auth |
| SEC-009 | Dependency Scanning | High | Known vulnerabilities in dependencies |
| SEC-010 | Security Headers | Medium | CSP, HSTS, X-Frame-Options |
| SEC-011 | Session Management | High | Secure session handling, timeout |
| SEC-012 | Error Handling | Medium | No sensitive data in error messages |
| SEC-013 | Cryptography Standards | High | Modern algorithms, no deprecated crypto |
| SEC-014 | Zero Trust Principles | High | Never trust, always verify |
| SEC-015 | Secure Defaults | High | Fail-secure, least privilege |
| SEC-016 | MFA Implementation | High | Multi-factor authentication support |
| SEC-017 | Password Policy | Medium | NIST 800-63 compliant password rules |
| SEC-018 | CSRF Protection | High | Cross-site request forgery prevention |
| SEC-019 | XSS Prevention | Critical | Cross-site scripting mitigation |
| SEC-020 | SQL Injection Prevention | Critical | Parameterized queries, ORM usage |
| SEC-021 | File Upload Security | High | Type validation, size limits, scanning |
| SEC-022 | Secure Communications | Critical | TLS 1.2+, certificate validation |
| SEC-023 | Container Security | High | Base image scanning, minimal images |
| SEC-024 | Infrastructure as Code Security | High | IaC security scanning |
| SEC-025 | Supply Chain Security | Critical | SBOM, signed artifacts |

---

## DOMAIN 3: COMPLIANCE (COMP)

**Purpose**: Ensure software meets regulatory and industry compliance requirements.

### Regulatory Frameworks

#### Data Privacy
- **GDPR** - EU General Data Protection Regulation
- **CCPA/CPRA** - California Consumer Privacy Act
- **LGPD** - Brazil's General Data Protection Law
- **PIPEDA** - Canada's Personal Information Protection

#### Healthcare
- **HIPAA** - Health Insurance Portability and Accountability Act
- **HITECH** - Health Information Technology for Economic and Clinical Health
- **FDA 21 CFR Part 11** - Electronic Records/Signatures

#### Financial
- **PCI-DSS 4.0** - Payment Card Industry Data Security Standard
- **SOX** - Sarbanes-Oxley Act
- **GLBA** - Gramm-Leach-Bliley Act

#### Government/Defense (US)
- **FedRAMP** - Federal Risk and Authorization Management Program
- **CMMC 2.0** - Cybersecurity Maturity Model Certification (DoD contractors)
- **FISMA** - Federal Information Security Management Act
- **NIST 800-171** - Protecting Controlled Unclassified Information
- **ITAR** - International Traffic in Arms Regulations
- **EAR** - Export Administration Regulations

#### Industry Standards
- **SOC 2 Type I/II** - Service Organization Control (Trust Services Criteria)
- **ISO 27001** - Information Security Management System
- **ISO 27017** - Cloud Security
- **ISO 27018** - PII in Public Clouds
- **ISO 27701** - Privacy Information Management

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| COMP-001 | Data Classification | High | Data categorized by sensitivity |
| COMP-002 | Privacy by Design | High | Privacy embedded in architecture |
| COMP-003 | Consent Management | Critical | User consent properly obtained/stored |
| COMP-004 | Data Subject Rights | Critical | DSAR handling (access, deletion, portability) |
| COMP-005 | Data Retention Policy | High | Retention periods defined and enforced |
| COMP-006 | Cross-Border Transfer | High | International data transfer compliance |
| COMP-007 | Breach Notification | Critical | Incident response and notification procedures |
| COMP-008 | Audit Trail | High | Complete audit trail for compliance evidence |
| COMP-009 | Access Controls | Critical | Role-based access to sensitive data |
| COMP-010 | Vendor Management | High | Third-party compliance requirements |
| COMP-011 | Documentation | High | Policies, procedures, evidence documented |
| COMP-012 | Training Records | Medium | Staff compliance training tracked |
| COMP-013 | Risk Assessment | High | Regular compliance risk assessments |
| COMP-014 | Regulatory Mapping | Medium | Requirements mapped to controls |
| COMP-015 | Change Control | High | Compliance impact of changes assessed |

---

## DOMAIN 4: DOD/GOVERNMENT (GOV)

**Purpose**: Meet US Department of Defense and federal government security requirements.

### Standards & Frameworks
- **DISA STIGs** - Security Technical Implementation Guides (~500 STIGs)
- **CSRMC** - Cybersecurity Risk Management Construct (replacing RMF)
- **RMF** - Risk Management Framework (legacy, being replaced)
- **CMMC 2.0** - Cybersecurity Maturity Model Certification
- **NIST SP 800-53 Rev 5** - Security and Privacy Controls
- **NIST SP 800-171 Rev 2** - Protecting CUI
- **DoD DevSecOps Reference Design** - Software Factory standards
- **Zero Trust (DoD)** - FY2027 implementation deadline
- **cATO** - Continuous Authority to Operate

### STIG Categories
- CAT I (High) - Vulnerabilities allowing immediate system compromise
- CAT II (Medium) - Vulnerabilities potentially leading to compromise
- CAT III (Low) - Degradation of security posture

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| GOV-001 | STIG Compliance | Critical | Applicable STIGs implemented |
| GOV-002 | CMMC Level | Critical | Required CMMC level achieved |
| GOV-003 | CUI Handling | Critical | Controlled Unclassified Information protected |
| GOV-004 | FCI Protection | High | Federal Contract Information secured |
| GOV-005 | NIST 800-171 Controls | Critical | All 110 controls implemented |
| GOV-006 | NIST 800-53 Controls | Critical | Selected control baseline implemented |
| GOV-007 | POA&M | High | Plan of Action and Milestones current |
| GOV-008 | System Security Plan | Critical | SSP documented and approved |
| GOV-009 | Continuous Monitoring | High | Ongoing assessment and authorization |
| GOV-010 | Incident Reporting | Critical | 72-hour DFARS reporting capability |
| GOV-011 | Supply Chain Risk | High | SCRM program implemented |
| GOV-012 | Zero Trust Architecture | High | ZTA principles implemented |
| GOV-013 | DevSecOps Pipeline | High | DoD DevSecOps Reference Design compliance |
| GOV-014 | ATO Documentation | Critical | Authority to Operate package complete |
| GOV-015 | FIPS 140-2/3 | High | Cryptographic module validation |

---

## DOMAIN 5: NSA GUIDANCE (NSA)

**Purpose**: Implement NSA cybersecurity best practices and zero trust architecture.

### NSA Cybersecurity Guidance Documents
- **Zero Trust Implementation Guidelines (ZIG)** - January 2025
- **Application and Workload Pillar** - October 2024
- **Network and Environment Pillar** - March 2024
- **Data Pillar** - April 2024
- **User Pillar** - April 2023
- **Device Pillar** - February 2024
- **AI Data Security Best Practices** - May 2025
- **Embracing Zero Trust Security Model** - February 2021

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| NSA-001 | Never Trust, Always Verify | Critical | Zero trust core principle |
| NSA-002 | Strong MFA | Critical | Multi-factor authentication required |
| NSA-003 | Micro-Segmentation | High | Network segmentation limits lateral movement |
| NSA-004 | Least Privilege | Critical | Minimum necessary access |
| NSA-005 | Continuous Authentication | High | Ongoing identity verification |
| NSA-006 | Encryption Everywhere | Critical | Data encrypted at rest, in transit, in use |
| NSA-007 | Quantum-Resistant Crypto | High | Post-quantum cryptographic standards |
| NSA-008 | API Security | High | APIs secured with auth, authz, encryption |
| NSA-009 | Secure Enclaves | Medium | Hardware-based isolation for sensitive ops |
| NSA-010 | Data Flow Mapping | High | Understanding how data moves through system |
| NSA-011 | Continuous Monitoring | High | Real-time security posture assessment |
| NSA-012 | Software Defined Networking | Medium | SDN for network control |
| NSA-013 | Host Isolation | High | Workload isolation capabilities |
| NSA-014 | Digital Signatures | High | Datasets and artifacts signed |
| NSA-015 | AI/ML Data Protection | High | Training data integrity and confidentiality |

---

## DOMAIN 6: PERFORMANCE (PERF)

**Purpose**: Ensure software meets performance requirements under expected and peak loads.

### Standards & Frameworks
- ISO/IEC 25010 (Performance Efficiency characteristic)
- Google Core Web Vitals
- Apdex (Application Performance Index)

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| PERF-001 | Response Time | High | P95/P99 latency within targets |
| PERF-002 | Throughput | High | Transactions per second meets requirements |
| PERF-003 | Resource Utilization | Medium | CPU, memory, disk within bounds |
| PERF-004 | Scalability | High | Linear scaling under load |
| PERF-005 | Load Testing | High | Performance under expected load verified |
| PERF-006 | Stress Testing | High | Behavior under peak/beyond-peak load known |
| PERF-007 | Endurance Testing | Medium | Performance stable over extended periods |
| PERF-008 | Database Performance | High | Query optimization, indexing verified |
| PERF-009 | Caching Strategy | Medium | Appropriate caching implemented |
| PERF-010 | CDN Utilization | Medium | Static assets served from CDN |
| PERF-011 | API Performance | High | API response times meet SLA |
| PERF-012 | Memory Leaks | High | No memory leaks under sustained load |
| PERF-013 | Connection Pooling | Medium | Database connections efficiently managed |
| PERF-014 | Async Processing | Medium | Long-running tasks handled asynchronously |
| PERF-015 | Performance Budgets | Medium | Page load budgets defined and met |

---

## DOMAIN 7: RELIABILITY (REL)

**Purpose**: Ensure software is available, fault-tolerant, and recoverable.

### Standards & Frameworks
- ISO/IEC 25010 (Reliability characteristic)
- SRE (Site Reliability Engineering) principles
- Chaos Engineering principles

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| REL-001 | Availability Target | Critical | SLA/SLO defined (e.g., 99.9%) |
| REL-002 | Fault Tolerance | High | Graceful degradation under failures |
| REL-003 | Redundancy | High | No single points of failure |
| REL-004 | Disaster Recovery | Critical | DR plan documented and tested |
| REL-005 | Backup Strategy | Critical | Backups automated, tested, offsite |
| REL-006 | Recovery Time Objective | Critical | RTO defined and achievable |
| REL-007 | Recovery Point Objective | Critical | RPO defined and achievable |
| REL-008 | Health Checks | High | Liveness and readiness probes |
| REL-009 | Circuit Breakers | High | Cascading failure prevention |
| REL-010 | Retry Logic | Medium | Transient failure handling |
| REL-011 | Timeout Configuration | Medium | Appropriate timeouts set |
| REL-012 | Chaos Testing | Medium | Failure injection testing performed |
| REL-013 | Failover Testing | High | Failover procedures verified |
| REL-014 | Data Integrity | Critical | Data consistency maintained |
| REL-015 | Runbook Documentation | High | Operational procedures documented |

---

## DOMAIN 8: INTEGRATION (INT)

**Purpose**: Ensure components integrate correctly and APIs function as specified.

### Standards & Frameworks
- OpenAPI Specification 3.x
- AsyncAPI
- GraphQL specification
- Contract testing (Pact)

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| INT-001 | E2E Flow Coverage | Critical | End-to-end user flows tested |
| INT-002 | Acceptance Criteria Validated | Critical | PRD acceptance criteria verified |
| INT-003 | API Contract Compliance | Critical | APIs match specification |
| INT-004 | Contract Testing | High | Provider/consumer contracts verified |
| INT-005 | Data Exchange Validation | High | Data formats and schemas validated |
| INT-006 | Third-Party Integration | High | External service integrations tested |
| INT-007 | Data Integrity | Critical | Data consistency across systems |
| INT-008 | Error Recovery | High | Integration failure handling |
| INT-009 | Backward Compatibility | High | API versioning, no breaking changes |
| INT-010 | Integration Performance | Medium | Cross-system latency acceptable |
| INT-011 | Message Queue Integration | Medium | Async messaging verified |
| INT-012 | Webhook Reliability | Medium | Webhook delivery and retry |
| INT-013 | Authentication Flow | Critical | Cross-system auth works correctly |
| INT-014 | Data Transformation | Medium | ETL/transformation accuracy |
| INT-015 | Service Mesh | Medium | Service-to-service communication |

---

## DOMAIN 9: OBSERVABILITY (OBS)

**Purpose**: Ensure software is observable through logs, metrics, and traces.

### Standards & Frameworks
- OpenTelemetry
- Prometheus metrics format
- ELK/EFK stack patterns
- SRE Golden Signals

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| OBS-001 | Structured Logging | High | Consistent, parseable log format |
| OBS-002 | Log Levels | Medium | Appropriate log level usage |
| OBS-003 | Metrics Collection | High | Key metrics instrumented |
| OBS-004 | Distributed Tracing | High | Request tracing across services |
| OBS-005 | Alerting Rules | Critical | Actionable alerts configured |
| OBS-006 | Dashboard Coverage | Medium | Key metrics visualized |
| OBS-007 | Log Retention | Medium | Retention policy implemented |
| OBS-008 | Correlation IDs | High | Request tracking across systems |
| OBS-009 | Error Tracking | High | Exceptions captured and grouped |
| OBS-010 | SLI/SLO Monitoring | High | Service level indicators tracked |
| OBS-011 | Anomaly Detection | Medium | Automated anomaly alerting |
| OBS-012 | Capacity Monitoring | Medium | Resource utilization tracked |
| OBS-013 | Security Event Logging | Critical | Security events captured |
| OBS-014 | Audit Logging | High | User actions logged |
| OBS-015 | Log Aggregation | Medium | Centralized log management |

---

## DOMAIN 10: DEPLOYMENT (DEP)

**Purpose**: Ensure reliable, repeatable, and safe deployment processes.

### Standards & Frameworks
- DORA metrics (Deployment Frequency, Lead Time, MTTR, Change Failure Rate)
- GitOps principles
- 12-Factor App methodology

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| DEP-001 | CI/CD Pipeline | High | Automated build and deployment |
| DEP-002 | Infrastructure as Code | High | IaC for all infrastructure |
| DEP-003 | Rollback Procedure | Critical | Quick rollback capability |
| DEP-004 | Blue-Green/Canary | High | Progressive deployment strategy |
| DEP-005 | Environment Parity | High | Dev/staging/prod consistency |
| DEP-006 | Deployment Automation | High | No manual deployment steps |
| DEP-007 | Secrets Injection | Critical | Secrets injected at runtime |
| DEP-008 | Health Check Integration | High | Deployment health verification |
| DEP-009 | Version Tagging | Medium | Semantic versioning, git tags |
| DEP-010 | Artifact Management | Medium | Immutable, versioned artifacts |
| DEP-011 | Database Migrations | High | Automated, reversible migrations |
| DEP-012 | Feature Flags | Medium | Gradual feature rollout capability |
| DEP-013 | Deployment Documentation | Medium | Runbooks, procedures documented |
| DEP-014 | Change Approval | High | Change management process |
| DEP-015 | Post-Deployment Verification | High | Smoke tests after deployment |

---

## DOMAIN 11: DATA MANAGEMENT (DATA)

**Purpose**: Ensure data is properly modeled, validated, and managed.

### Standards & Frameworks
- Data Management Body of Knowledge (DMBOK)
- Master Data Management (MDM) patterns
- Data Quality dimensions (accuracy, completeness, consistency, timeliness)

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| DATA-001 | Data Model Documentation | High | Schema documented and versioned |
| DATA-002 | Data Validation | High | Input validation at boundaries |
| DATA-003 | Referential Integrity | High | Foreign key constraints enforced |
| DATA-004 | Data Migration | High | Migration scripts tested, reversible |
| DATA-005 | Data Archival | Medium | Archival policy implemented |
| DATA-006 | Data Quality | High | Quality metrics defined and monitored |
| DATA-007 | Master Data Management | Medium | Authoritative data sources identified |
| DATA-008 | Data Lineage | Medium | Data origin and transformations tracked |
| DATA-009 | Schema Evolution | High | Backward-compatible schema changes |
| DATA-010 | Data Classification | Critical | Sensitivity levels assigned |
| DATA-011 | PII Handling | Critical | Personal data properly protected |
| DATA-012 | Data Anonymization | High | Anonymization for non-prod environments |
| DATA-013 | Backup Verification | Critical | Backup restore tested |
| DATA-014 | Data Governance | Medium | Ownership and stewardship defined |
| DATA-015 | CRUD Operations | Medium | All data operations audited |

---

## DOMAIN 12: USER EXPERIENCE (UX)

**Purpose**: Ensure software is accessible, usable, and provides good user experience.

### Standards & Frameworks
- **WCAG 2.2** - Web Content Accessibility Guidelines
- **Section 508** - US Federal accessibility requirements
- **ADA** - Americans with Disabilities Act
- **EN 301 549** - EU accessibility standard
- ISO/IEC 25010 (Usability characteristic)
- Nielsen's Usability Heuristics

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| UX-001 | WCAG Level A | Critical | Level A accessibility criteria met |
| UX-002 | WCAG Level AA | High | Level AA accessibility criteria met |
| UX-003 | Keyboard Navigation | Critical | Full keyboard accessibility |
| UX-004 | Screen Reader Support | Critical | Proper ARIA labels, semantic HTML |
| UX-005 | Color Contrast | High | 4.5:1 contrast ratio minimum |
| UX-006 | Focus Indicators | High | Visible focus states |
| UX-007 | Alternative Text | Critical | Images have descriptive alt text |
| UX-008 | Form Accessibility | High | Labels, error messages accessible |
| UX-009 | Responsive Design | High | Works across device sizes |
| UX-010 | Loading Performance | Medium | Core Web Vitals met |
| UX-011 | Error Messages | Medium | Clear, actionable error messages |
| UX-012 | Consistent Navigation | Medium | Predictable UI patterns |
| UX-013 | VPAT Documentation | High | Accessibility conformance report |
| UX-014 | User Testing | Medium | Tested with users with disabilities |
| UX-015 | Internationalization | Medium | Locale and language support |

---

## DOMAIN 13: MAINTAINABILITY (MAINT)

**Purpose**: Ensure software is maintainable, readable, and properly documented.

### Standards & Frameworks
- ISO/IEC 25010 (Maintainability characteristic)
- CISQ Code Quality measures
- Clean Code principles
- SOLID principles

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| MAINT-001 | Code Organization | Medium | Logical module/package structure |
| MAINT-002 | Naming Conventions | Medium | Consistent, descriptive naming |
| MAINT-003 | Test Coverage | High | Coverage target met (e.g., 80%) |
| MAINT-004 | Test Quality | High | Tests are meaningful, not just coverage |
| MAINT-005 | Technical Documentation | Medium | Architecture, API docs current |
| MAINT-006 | Code Comments | Low | Complex logic explained |
| MAINT-007 | Dependency Management | High | Dependencies tracked, updated |
| MAINT-008 | Code Duplication | Medium | DRY principle followed |
| MAINT-009 | Complexity Metrics | Medium | Cyclomatic complexity within bounds |
| MAINT-010 | Linting/Formatting | Medium | Consistent code style enforced |
| MAINT-011 | Static Analysis | High | Code quality tools configured |
| MAINT-012 | Modular Design | High | Low coupling, high cohesion |
| MAINT-013 | API Documentation | High | OpenAPI/Swagger specs current |
| MAINT-014 | Deprecation Policy | Medium | Deprecated features documented |
| MAINT-015 | Technical Debt Tracking | Medium | Tech debt documented, prioritized |

---

## DOMAIN 14: TESTING (TEST)

**Purpose**: Ensure comprehensive testing strategy and execution.

### Standards & Frameworks
- **ISO/IEC/IEEE 29119** - Software Testing Standard (5 parts)
- **IEEE 829** - Test Documentation (superseded by 29119-3)
- **ISTQB** - Testing certification body of knowledge
- Testing Pyramid (Unit > Integration > E2E)

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| TEST-001 | Test Strategy | High | Testing approach documented |
| TEST-002 | Unit Test Coverage | High | Unit tests cover critical paths |
| TEST-003 | Integration Tests | High | Component integration verified |
| TEST-004 | E2E Tests | High | End-to-end user flows tested |
| TEST-005 | Test Automation | High | Tests automated in CI/CD |
| TEST-006 | Test Data Management | Medium | Test data strategy defined |
| TEST-007 | Regression Testing | High | Regression suite maintained |
| TEST-008 | Smoke Tests | High | Critical path smoke tests |
| TEST-009 | Test Environment | Medium | Dedicated test environments |
| TEST-010 | Mutation Testing | Low | Test quality verified via mutations |
| TEST-011 | Property-Based Testing | Low | Generative testing for edge cases |
| TEST-012 | Visual Regression | Medium | UI changes detected |
| TEST-013 | API Testing | High | API contracts tested |
| TEST-014 | Test Documentation | Medium | Test plans, cases documented |
| TEST-015 | Defect Tracking | Medium | Bugs tracked to resolution |

---

## DOMAIN 15: ARCHITECTURE (ARCH)

**Purpose**: Ensure software architecture is sound, documented, and followed.

### Standards & Frameworks
- ISO/IEC/IEEE 42010 - Architecture Description
- C4 Model
- arc42 Template
- Domain-Driven Design (DDD)

### Audit Dimensions
| ID | Name | Severity | Description |
|----|------|----------|-------------|
| ARCH-001 | Architecture Documentation | High | ADRs, diagrams current |
| ARCH-002 | Design Patterns | Medium | Appropriate patterns used |
| ARCH-003 | Separation of Concerns | High | Clear layer boundaries |
| ARCH-004 | API Design | High | RESTful/GraphQL best practices |
| ARCH-005 | Event-Driven Design | Medium | Async patterns properly used |
| ARCH-006 | Microservices Boundaries | High | Service boundaries well-defined |
| ARCH-007 | Data Architecture | High | Data flow and storage designed |
| ARCH-008 | Scalability Design | High | Horizontal scaling possible |
| ARCH-009 | Security Architecture | Critical | Security designed in |
| ARCH-010 | Infrastructure Architecture | High | Cloud/infra architecture documented |
| ARCH-011 | Integration Architecture | High | External integrations designed |
| ARCH-012 | Caching Architecture | Medium | Caching strategy designed |
| ARCH-013 | Resilience Patterns | High | Circuit breakers, bulkheads designed |
| ARCH-014 | Technology Choices | Medium | Tech stack decisions documented |
| ARCH-015 | Technical Constraints | Medium | Constraints documented and followed |

---

## Summary Statistics

| Domain | Code | Audit Count | Critical | High | Medium | Low |
|--------|------|-------------|----------|------|--------|-----|
| Requirements | REQ | 15 | 2 | 6 | 7 | 0 |
| Security | SEC | 25 | 8 | 13 | 4 | 0 |
| Compliance | COMP | 15 | 4 | 8 | 3 | 0 |
| DoD/Government | GOV | 15 | 8 | 6 | 1 | 0 |
| NSA Guidance | NSA | 15 | 4 | 8 | 3 | 0 |
| Performance | PERF | 15 | 0 | 7 | 8 | 0 |
| Reliability | REL | 15 | 5 | 7 | 3 | 0 |
| Integration | INT | 15 | 4 | 7 | 4 | 0 |
| Observability | OBS | 15 | 2 | 7 | 6 | 0 |
| Deployment | DEP | 15 | 2 | 9 | 4 | 0 |
| Data Management | DATA | 15 | 3 | 7 | 5 | 0 |
| User Experience | UX | 15 | 4 | 6 | 5 | 0 |
| Maintainability | MAINT | 15 | 0 | 5 | 9 | 1 |
| Testing | TEST | 15 | 0 | 8 | 5 | 2 |
| Architecture | ARCH | 15 | 1 | 9 | 5 | 0 |
| **TOTAL** | | **225** | **47** | **113** | **72** | **3** |

---

## Sources

### Frameworks & Standards
- [NIST Secure Software Development Framework (SSDF)](https://csrc.nist.gov/projects/ssdf)
- [NIST SP 800-218](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-218.pdf)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP MASVS](https://mas.owasp.org/MASVS/)
- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html)
- [ISO/IEC/IEEE 29119](https://en.wikipedia.org/wiki/ISO/IEC_29119)

### Government/Defense
- [DISA STIGs](https://resources.steelpatriotpartners.com/security-technical-implementation-guides-stigs)
- [DoD CSRMC](https://www.compliancehub.wiki/the-end-of-rmf-understanding-the-dods-revolutionary-cyber-security-risk-management-construct-csrmc/)
- [CMMC 2.0](https://www.sonatype.com/blog/cmmc-2.0-in-action-operationalizing-secure-software-practices-across-the-defense-industrial-base)
- [DoD DevSecOps Guidebook](https://www.cto.mil/wp-content/uploads/2025/01/Software_DTE_DEVSECOPS_GB_Jan2025_Signed.pdf)
- [NSA Zero Trust Guidelines](https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/4378980/nsa-releases-first-in-series-of-zero-trust-implementation-guidelines/)
- [NSA AI Data Security](https://www.dwt.com/blogs/privacy--security-law-blog/2025/06/nsa-cybersecurity-guidance-for-ai)

### Compliance
- [SOC 2/ISO 27001/HIPAA/GDPR Overview](https://sprinto.com/blog/compliance-standards/)
- [Section 508 Compliance](https://www.section508.gov/)
- [WCAG 2.2](https://www.wcag.com/compliance/section-508/)
