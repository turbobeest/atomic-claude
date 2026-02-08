# Cloud Well-Architected Framework - Six Pillars

> **Sources**:
> - AWS: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
> - Azure: https://learn.microsoft.com/en-us/azure/well-architected/
> - GCP: https://cloud.google.com/architecture/framework
> **Extracted**: 2025-12-21
> **Refresh**: Quarterly (frameworks update frequently)

## The Six Pillars (Cross-Cloud Consensus)

### 1. Operational Excellence
**Focus**: Run and monitor systems to deliver business value, continuously improve processes

**Key Practices**:
- Perform operations as code (IaC)
- Make frequent, small, reversible changes
- Refine operations procedures frequently
- Anticipate failure and learn from all operational events
- Use managed services to reduce operational burden

**Metrics**: Deployment frequency, change failure rate, MTTR

### 2. Security
**Focus**: Protect information, systems, and assets through risk assessments and mitigation

**Key Practices**:
- Implement a strong identity foundation (least privilege, MFA)
- Enable traceability (logging, monitoring, alerting)
- Apply security at all layers (network, compute, data)
- Automate security best practices
- Protect data in transit and at rest
- Keep people away from data (automation)
- Prepare for security events (incident response)

**Metrics**: Time to detect, time to remediate, compliance score

### 3. Reliability
**Focus**: Ensure workloads perform intended functions correctly and consistently

**Key Practices**:
- Automatically recover from failure
- Test recovery procedures
- Scale horizontally to increase aggregate availability
- Stop guessing capacity (auto-scaling)
- Manage change through automation

**Metrics**: Availability (nines), MTBF, MTTR, RTO, RPO

### 4. Performance Efficiency
**Focus**: Use computing resources efficiently to meet requirements as demand changes

**Key Practices**:
- Democratize advanced technologies (managed services)
- Go global in minutes (multi-region)
- Use serverless architectures where appropriate
- Experiment more often
- Consider mechanical sympathy (right tool for job)

**Metrics**: Latency (p50, p95, p99), throughput, resource utilization

### 5. Cost Optimization
**Focus**: Avoid unnecessary costs and run systems at lowest price point

**Key Practices**:
- Implement cloud financial management
- Adopt consumption model (pay for what you use)
- Measure overall efficiency
- Stop spending on undifferentiated heavy lifting
- Analyze and attribute expenditure

**Metrics**: Cost per transaction, resource utilization, reserved vs on-demand ratio

### 6. Sustainability (Newest Pillar)
**Focus**: Minimize environmental impact of cloud workloads

**Key Practices**:
- Understand your impact
- Establish sustainability goals
- Maximize utilization
- Anticipate and adopt new, more efficient offerings
- Use managed services
- Reduce downstream impact of your workloads

**Metrics**: Carbon footprint, energy efficiency, resource utilization

## Cloud-Specific Variations

| Pillar | AWS Term | Azure Term | GCP Term |
|--------|----------|------------|----------|
| Operational Excellence | Same | Same | Operational Excellence |
| Security | Same | Same | Security, Privacy, Compliance |
| Reliability | Same | Same | Reliability |
| Performance Efficiency | Same | Performance Efficiency | Performance Optimization |
| Cost Optimization | Same | Cost Optimization | Cost Optimization |
| Sustainability | Same | Sustainability | Sustainability (Preview) |

## Design Principles Summary

1. **Stop guessing your capacity needs** - Use auto-scaling
2. **Test systems at production scale** - Create production-equivalent test environments
3. **Automate to make architectural experimentation easier** - IaC enables rapid iteration
4. **Allow for evolutionary architectures** - Design for change
5. **Drive architectures using data** - Collect metrics, make informed decisions
6. **Improve through game days** - Simulate production events

---
*This excerpt was curated for agent knowledge grounding. See source URLs for full context.*
