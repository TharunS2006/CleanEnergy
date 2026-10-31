import json, pathlib
R = json.load(open(pathlib.Path(__file__).parent.parent / "bench_results.json"))
D = R["designs"]; B, S, G, F = D["basic"], D["segmented"], D["resilient"], D["basic+fixes"]
ABSTRACT = (
    "A virtualized data centre runs many services on a small number of shared hosts, networks, power feeds and storage arrays. A design is "
    "judged on three questions that depend on one another: does the capacity fit and survive the loss of a host, are the network zones "
    "separated so that an attacker cannot reach the databases from the internet, and does any single failure take a service down. Design "
    "reviews usually answer them by checklist. This mini project builds a tool that answers them by calculation, using only the Python standard library. "
    "A design is described as hosts, racks, power feeds, switches, cooling units, firewalls, storage arrays, virtual machines and firewall rules. "
    "The capacity module places VMs with anti-affinity and tests N+1. The security module applies first-match firewall semantics, compares the rules "
    "with an intended three-tier policy, finds routes from the internet to the critical zones and scores a hardening checklist. The resilience module fails every component "
    "and every pair of components in turn, finds single points of failure, simulates the availability of each service, and gives a simplified tier classification. "
    f"Three reference designs were evaluated. The basic flat design scored {B['overall']:.0f} out of 100, with {B['counts']['critical']} critical findings, a one-hop route from the internet to the database, "
    f"{len(B['spofs'])} single points of failure and {B['e2e_down_min'] / 60:.1f} hours of simulated downtime a year; the resilient design scored {G['overall']:.0f}, with no route shorter than three hops, "
    f"no single point of failure and {G['e2e_down_min']:.1f} minutes of downtime a year. An automatic remediation lifted the basic design to {F['overall']:.0f}, but left nine process items for people. "
    f"Every one of {R['detection']['injected']} injected firewall mistakes was detected. A command-line tool and a browser interface are provided, and 34 automated tests pass.")
