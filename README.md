# Setup
* Create an [Oracle Cloud account](https://www.oracle.com/cloud/)
  * Potentially optional? but I created a `VM.Standard.E2.1.Micro` instance first just to make sure all the VNIC and subnet stuff already existed
* Set up your OCI config
  * I used the [CLI](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm) and did the interactive method
  * this defaults your config to `~/.oci/config`, which makes it easy to access in the script
* Make sure you have `uv` [installed](https://docs.astral.sh/uv/getting-started/installation/)
* Clone the repo with `git clone https://github.com/no-waves/arm-grab.git`

# Usage
`uv run arm-grab.py` from the repo folder
