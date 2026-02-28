# Contributing to the Audit Taxonomy

Thank you for your interest in contributing to the Software Stack Audit Taxonomy.

## Ways to Contribute

1. **Add new audit files** - Create YAML audit definitions for categories/subcategories
2. **Improve existing audits** - Enhance signals, remediation guidance, or verification commands
3. **Add industry overlays** - Create industry-specific audit extensions
4. **Improve tooling** - Add scripts, Semgrep rules, or PromQL queries
5. **Documentation** - Improve guides, examples, or architecture docs

## Audit File Guidelines

### Before Writing an Audit

1. Check `AUDIT-MENU.md` to confirm the audit doesn't already exist
2. Review `schema/examples/README.md` to select the appropriate pattern:
   - **Organizational pattern** (`01-bus-factor-audit.yaml`) - For human/team assessments
   - **Infrastructure pattern** (`02-container-resource-limits-audit.yaml`) - For metrics/config checks
   - **Documentation pattern** (`03-runbook-completeness-audit.yaml`) - For process/artifact review
   - **Code/Security pattern** (`schema/AUDIT-TEMPLATE-BLANK.yaml`) - For code analysis

### Audit Quality Checklist

- [ ] Hierarchical ID follows convention: `{category}.{subcategory}.{audit-slug}`
- [ ] At least 2 critical and 2 high severity signals defined
- [ ] Each signal has specific, actionable remediation guidance
- [ ] Verification commands are syntactically valid (if applicable)
- [ ] Knowledge sources are authoritative (OWASP, NIST, RFCs, etc.)
- [ ] Appropriate profile membership (quick/security/production/full)
- [ ] Related audits are cross-referenced

### File Naming Convention

```
audits/{nn}-{category-slug}/{subcategory-slug}/{audit-slug}.yaml
```

Example: `audits/01-security-trust/authentication/session-management.yaml`

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/add-xyz-audit`
3. Make your changes
4. Run validation: `./validation/validate-all.sh`
5. Commit with clear message: `Add XYZ audit to security-trust.authentication`
6. Push and create a Pull Request

## Code of Conduct

- Be respectful and constructive
- Focus on audit quality and accuracy
- Cite authoritative sources
- Test verification commands before submitting

## Questions?

Open an issue for discussion or clarification.
