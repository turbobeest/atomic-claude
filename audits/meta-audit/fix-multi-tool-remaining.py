#!/usr/bin/env python3
"""Add multi-tool commands to remaining files."""

from pathlib import Path

AUDITS_ROOT = Path("/mnt/walnut-drive/dev/audits/audits")

ADDITIONS = {
    "11-devops-ci-cd/infrastructure-as-code/iac-security-scanning.yaml": """
  # Multi-tool IaC security scanning:
  # Terraform:
  #   tflint --recursive
  #   checkov -d . --framework terraform
  #   tfsec .
  #   terrascan scan -i terraform
  # Pulumi:
  #   pulumi preview --json | jq '.steps[].diagnostics'
  # CloudFormation:
  #   cfn-lint template.yaml
  #   cfn_nag_scan --input-path template.yaml
  # CDK:
  #   cdk synth && checkov -f cdk.out/*.template.json
  # Ansible:
  #   ansible-lint playbook.yaml
  # Generic:
  #   snyk iac test
  #   trivy config .
""",

    "12-cloud-infrastructure/containers/container-image-security.yaml": """
  # Multi-tool container image security:
  # Trivy:
  #   trivy image ${IMAGE}:${TAG}
  #   trivy image --severity HIGH,CRITICAL ${IMAGE}
  # Grype:
  #   grype ${IMAGE}:${TAG}
  #   grype ${IMAGE} -o json
  # Snyk:
  #   snyk container test ${IMAGE}:${TAG}
  # Docker Scout:
  #   docker scout cves ${IMAGE}:${TAG}
  #   docker scout recommendations ${IMAGE}
  # Clair:
  #   clairctl report ${IMAGE}
  # Anchore:
  #   anchore-cli image add ${IMAGE}
  #   anchore-cli image vuln ${IMAGE} all
""",

    "11-devops-ci-cd/pipeline-security/pipeline-access-control.yaml": """
  # Multi-platform CI/CD access control checks:
  # GitHub Actions:
  #   gh api repos/{owner}/{repo}/actions/permissions
  #   gh api repos/{owner}/{repo}/environments
  # GitLab CI:
  #   glab api projects/:id/protected_branches
  #   glab api projects/:id/members
  # Jenkins:
  #   curl -s ${JENKINS_URL}/api/json?tree=jobs[name,permissions]
  # Azure DevOps:
  #   az devops security permission list --id ${PROJECT_ID}
  # CircleCI:
  #   circleci context list
  #   circleci orb list
""",

    "02-performance-efficiency/database-performance/slow-query-detection.yaml": """
  # Multi-database slow query detection:
  # PostgreSQL:
  #   SELECT query, calls, mean_exec_time, total_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;
  #   SELECT * FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 seconds';
  # MySQL:
  #   SELECT * FROM performance_schema.events_statements_summary_by_digest ORDER BY avg_timer_wait DESC LIMIT 20;
  #   SHOW FULL PROCESSLIST;
  # MongoDB:
  #   db.currentOp({"secs_running": {"$gt": 5}})
  #   db.system.profile.find({millis: {$gt: 100}}).sort({millis: -1}).limit(20)
  # Redis:
  #   redis-cli SLOWLOG GET 20
  #   redis-cli CLIENT LIST
  # Elasticsearch:
  #   GET /_nodes/hot_threads
  #   GET /_tasks?detailed=true&actions=*search
""",

    "13-infrastructure-as-code/testing-validation/iac-unit-testing.yaml": """
  # Multi-tool IaC testing:
  # Terraform:
  #   terraform test
  #   terratest (Go): go test -v ./test/
  #   terraform-compliance: terraform-compliance -p plan.out -f features/
  # Pulumi:
  #   pulumi preview --expect-no-changes
  #   pulumi up --dry-run
  # CloudFormation:
  #   taskcat test run
  #   cfn-guard validate -d template.yaml -r rules/
  # CDK:
  #   npm test (Jest assertions)
  #   cdk diff
  # Ansible:
  #   molecule test
  #   ansible-test sanity
""",
}

count = 0
for rel_path, commands in ADDITIONS.items():
    filepath = AUDITS_ROOT / rel_path
    if not filepath.exists():
        # Try to find similar file
        parts = rel_path.split('/')
        matches = list(AUDITS_ROOT.glob(f"**/{parts[-1]}"))
        if matches:
            filepath = matches[0]
        else:
            print(f"Skipped: {rel_path}")
            continue

    with open(filepath, 'r') as f:
        content = f.read()

    if "# Multi-" in content:
        print(f"Already has multi-tool: {filepath.name}")
        continue

    content = content.rstrip() + "\n" + commands
    with open(filepath, 'w') as f:
        f.write(content)
    count += 1
    print(f"Added: {filepath.name}")

print(f"\nTotal: {count} files updated")
