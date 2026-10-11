"""Section 3.8: cloud computing concepts (modules) and where CloudPulse applies each one.
No claim is made about when or where the concepts were studied."""


def modules(r):
    r.h(2, "3.8  Cloud Computing Concepts Applied in the Project")
    r.para("CloudPulse sits on top of several standard cloud computing topics. This section presents them as twelve short "
           "modules. Each module states the concept in brief and then the exact place where CloudPulse uses it, so that the "
           "theory can be traced to the implementation. Table 3.4 at the end of the section summarises the mapping.")

    mods = [
        ("Module 1: Cloud service and deployment models",
         "Cloud services are offered as Infrastructure as a Service (IaaS: virtual machines, disks and networks that the "
         "customer manages), Platform as a Service (PaaS: a managed run-time such as Azure App Service) and Software as a "
         "Service (SaaS: a finished application). Deployment models are public, private and hybrid cloud. Billing is "
         "pay-as-you-go: cost follows consumption.",
         "CloudPulse monitors IaaS resources (VMs, disks, public IPs, snapshots) that carry most avoidable cost, can itself be "
         "deployed as PaaS on App Service, and is delivered to users as a SaaS-style web application with one workspace per customer."),
        ("Module 2: Virtualisation and compute",
         "A virtual machine is a slice of a physical host with a chosen size (vCPU and memory). Burstable B-series sizes suit "
         "light workloads. A VM has a power state: when it is shut down from inside the operating system it is *stopped* but "
         "the hardware stays reserved and compute is still billed; only *deallocated* releases the hardware and stops the "
         "compute charge.",
         "The detector in `azure_collector.find_stopped_vms` separates the two states, and `analytics.vm_verdict` classifies "
         "running VMs as idle, oversized or fine from CPU and network metrics. The fix commands it suggests are "
         "`az vm deallocate` and `az vm delete`."),
        ("Module 3: Cloud storage",
         "Azure managed disks come in tiers (Standard HDD, Standard SSD and Premium SSD) and are billed per provisioned gigabyte "
         "whether or not a VM is using them. A snapshot is a point-in-time copy of a disk and is also billed by size. "
         "Detaching a VM does not delete its disks.",
         "Unattached disks (`diskState = Unattached`) and orphaned or old snapshots are two of the four waste rules in Table 5.1. "
         "`prices.py` converts size and tier to a monthly figure."),
        ("Module 4: Cloud networking",
         "A public IP address is a separate billable resource that can be associated with a network interface, a load balancer "
         "or a NAT gateway. A Standard-SKU static address is charged by the hour even when it is attached to nothing, "
         "while a dynamic address with nothing attached has no address and costs nothing.",
         "`find_idle_public_ips` reports static addresses with no `ipConfiguration` and no NAT gateway, and deliberately "
         "ignores dynamic ones."),
        ("Module 5: Identity and access management",
         "Access to cloud resources is controlled by an identity provider (Microsoft Entra ID), identities (users, service "
         "principals, managed identities) and role-based access control (RBAC) that grants roles at a scope. The principle of "
         "least privilege says an identity should have only the roles it needs. OAuth 2.0 access tokens prove who is calling.",
         "CloudPulse uses a service principal with only Reader and Cost Management Reader on one subscription, or a managed "
         "identity with no secret (Section 4.3). Its own users are separated by role: administrator, workspace owner and viewer."),
        ("Module 6: Resource management and governance",
         "Azure organises resources in tenants, subscriptions and resource groups under Azure Resource Manager (ARM). "
         "Tags attach metadata such as owner or team, and Azure Policy can restrict regions or require tags. Governance "
         "means being able to say who owns what and what it is for.",
         "Resource Graph queries the whole inventory in one call; owner tags are a fallback for ownership attribution; "
         "untagged spend becomes a governance finding; the scripts read the subscription's allowed-location policy."),
        ("Module 7: Monitoring and observability",
         "Azure Monitor collects platform metrics (for a VM: Percentage CPU, Network In Total and Network Out Total) with hourly or finer "
         "granularity. The Activity Log records control-plane operations, who performed them and when, for 90 days. "
         "Azure Advisor turns telemetry into recommendations in five categories, one of which is cost.",
         "Metrics feed the VM verdict, the Activity Log feeds the creator lookup in `owners.py` and `fetch_creator`, and "
         "Advisor items are merged into findings as supporting evidence."),
        ("Module 8: Cloud economics and pricing models",
         "Compute can be bought pay-as-you-go, with one- or three-year reservations or savings plans at a discount, or as "
         "interruptible Spot capacity. Retail prices are published in a public price list. Usage is billed "
         "after it happens and Azure publishes cost data with a delay of several hours.",
         "The price book reads the Retail Prices API with a cache and fallback tables, and cost data is back-filled for 90 days. "
         "The 8 to 24 hour delay is why verification waits for three billed days after a fix."),
        ("Module 9: FinOps",
         "FinOps is the practice of managing cloud cost through shared accountability. Its cycle is to inform (visibility "
         "and allocation), optimise (remove waste, rightsize, commit) and operate (govern continuously) [2], [20]. The "
         "Cost Optimization pillar of the Azure Well-Architected Framework expresses the same ideas.",
         "The whole cost-to-action loop is an implementation of that cycle: the Overview and Cost explorer inform, findings "
         "and priority optimise, and the lifecycle with verification operates."),
        ("Module 10: Elasticity, scaling and cost",
         "Elasticity means capacity can be added or removed quickly, which is why a short mistake, such as leaving a larger "
         "size running, appears on the bill within a day. Autoscaling and scheduled shutdown are the usual controls.",
         "`05-spike.sh up` scales the test workload for a day to create a real cost spike that the anomaly detector must "
         "flag, and `down` reverses it."),
        ("Module 11: Security and the shared responsibility model",
         "The provider secures the infrastructure; the customer secures its identities, data and configuration. Practical "
         "controls include encryption at rest, secret management, hashed passwords, rate limiting and read-only access.",
         "Stored cloud secrets use Fernet encryption, passwords use scrypt, sessions are server-side, and the collector issues "
         "only read requests (Table 4.4)."),
        ("Module 12: Automation, containers and DevOps",
         "Cloud resources are created repeatably with the command-line interface or infrastructure-as-code tools (ARM "
         "templates, Bicep, Terraform). Containers package an application with its dependencies, and continuous integration "
         "runs tests on every change.",
         "The Azure scripts use the CLI, the Dockerfile and `docker-compose.yml` package the application, `render.yaml` and "
         "`04-deploy-app.sh` deploy it, and GitHub Actions runs the 27 tests."),
    ]
    for title, concept, applied in mods:
        r.h(3, title)
        r.para("**Concept.** " + concept)
        r.para("**Applied in CloudPulse.** " + applied)

    r.table("Table 3.4: Cloud computing modules and where CloudPulse applies them",
            ["Module", "Concept", "Where in CloudPulse"],
            [["1", "Service and deployment models", "IaaS monitored; PaaS and SaaS delivery"],
             ["2", "Virtualisation and compute", "stopped vs deallocated VMs; idle and oversized verdict"],
             ["3", "Cloud storage", "unattached disks; orphaned snapshots"],
             ["4", "Cloud networking", "idle static public IPs"],
             ["5", "Identity and access management", "service principal, RBAC, managed identity, token flow"],
             ["6", "Resource management and governance", "Resource Graph, tags, untagged-spend finding"],
             ["7", "Monitoring and observability", "Azure Monitor, Activity Log, Advisor"],
             ["8", "Cloud economics and pricing", "price book, billing delay, 3-day verification wait"],
             ["9", "FinOps", "inform, optimise, operate = the cost-to-action loop"],
             ["10", "Elasticity and scaling", "05-spike.sh anomaly test"],
             ["11", "Security and shared responsibility", "Fernet, scrypt, read-only collector"],
             ["12", "Automation, containers, DevOps", "Azure CLI scripts, Docker, Render, App Service, CI"]],
            widths=[1.6, 5.4, 8.0], size=10)
