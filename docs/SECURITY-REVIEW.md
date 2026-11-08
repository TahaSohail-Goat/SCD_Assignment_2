# Review of completion-branch security findings

The SonarCloud gate reported unsafe artifact paths, a CLI-controlled network
destination, unverified downloaded Kubernetes resources, dependency installation,
and cleartext transports. The gate and its rating requirement remain enabled.

## Fixed in code

- Audit/report CLI paths are resolved and checked against dedicated repository
  artifact directories. Source paths and escapes outside the repository are
  rejected before deletion, directory creation or writing. Cache-case input is
  restricted to existing YAML files inside `eval/`. Regression tests cover escapes
  and attempts to overwrite source.
- Cache calibration accepts only a private/loopback Ollama origin on port 11434,
  rejects credentials and metadata/link-local/public/non-server destinations, pins
  the validated address for the request, disables redirects and ignores proxy
  environment variables. Tests cover malicious destinations and normal localhost.
- CD verifies the pinned Ingress manifest's committed SHA-256 before applying it.
- New audit dependencies use a complete Python 3.12/Linux lock with hashes and
  binary wheels only. The Ubuntu 24.04 Tesseract package version is pinned.
- The verifier's unnecessary backtracking expression was replaced by literal
  membership checks. Bash deployment uses `[[ ... ]]` for its condition.

## Narrow transport exceptions

Four HTTP locations carry explicit `NOSONAR` comments after review: the API's
shared local Ollama default, the corresponding ConfigMap entry, and two visible
rollout HTML fetches. These are assignment test-cluster transports. They do not
describe an Internet production deployment or a promise of transport encryption.

The host Ollama address is the Minikube bridge; the deployment helper resolves
that address and NetworkPolicy permits only its `/32` and port 11434. The operator
must keep Ollama on a trusted local network, with no public port forwarding. The
rollout script validates a private/loopback Ingress IP before fetching public UI
version labels; it transmits no credentials or user prompts. Loopback benchmark
service ports bind to `127.0.0.1` in the live audit workflow.

Using this system over an untrusted network requires TLS termination and proper
certificate validation. No global rule exclusion, quality-profile change, status
override, branch-protection relaxation or vulnerability acceptance was applied to
make the PR green. These line exceptions do not suppress the path, network-input
or supply-chain findings above.
