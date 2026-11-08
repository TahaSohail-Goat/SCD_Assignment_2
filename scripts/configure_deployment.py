"""Patch rendered prod objects with one explicit reachable Ollama host address."""

import argparse
import ipaddress
import sys
from urllib.parse import urlsplit

import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ollama-url", required=True)
    parser.add_argument("--ollama-cidr", required=True)
    parser.add_argument("--indexer-image", required=True)
    parser.add_argument("--api-image", default="rahbar-api:dev")
    parser.add_argument("--ui-image", default="rahbar-ui:dev")
    args = parser.parse_args()
    network = ipaddress.ip_network(args.ollama_cidr, strict=False)
    url = urlsplit(args.ollama_url)
    if network.version != 4 or network.prefixlen != 32:
        parser.error("use the resolved IPv4 host /32, not unrestricted egress")
    if url.scheme not in {"http", "https"} or url.port != 11434 or not url.hostname:
        parser.error("Ollama URL must name the host on port 11434")
    objects = list(yaml.safe_load_all(sys.stdin))
    for obj in objects:
        kind, name = obj["kind"], obj["metadata"]["name"]
        if kind == "ConfigMap" and name == "rahbar-config":
            obj["data"]["OLLAMA_URL"] = args.ollama_url
        if kind == "NetworkPolicy" and name in {"allow-api", "allow-indexer"}:
            for rule in obj["spec"].get("egress", []):
                for peer in rule.get("to", []):
                    if "ipBlock" in peer:
                        peer["ipBlock"]["cidr"] = str(network)
        if kind in {"Job", "CronJob"}:
            spec = obj["spec"] if kind == "Job" else obj["spec"]["jobTemplate"]["spec"]
            spec["template"]["spec"]["containers"][0]["image"] = args.indexer_image
        if kind == "Deployment" and name in {"api", "ui"}:
            obj["spec"]["template"]["spec"]["containers"][0]["image"] = (
                args.api_image if name == "api" else args.ui_image)
    yaml.safe_dump_all(objects, sys.stdout, sort_keys=False)


if __name__ == "__main__":
    main()
