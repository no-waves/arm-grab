"""
This script automates the process of launching an Oracle Cloud Infrastructure (OCI) instance
using the Python SDK. It retrieves configuration details, selects an appropriate Ubuntu image,
and attempts to launch instances in all available availability domains within a specified compartment.

Modules:
    - oci: Oracle Cloud Infrastructure Python SDK for interacting with OCI services.
    - os: Provides functions to interact with the operating system.
    - time: Used for adding delays between retries.
    - sys: Provides system-specific parameters and functions.

Functions:
    - create_instance_list() -> list[oci.core.models.LaunchInstanceDetails]:
        Creates a list of instance launch details for all availability domains in the compartment.
    - safe_sleep(duration) -> None:
        Sleeps for the specified duration, handling interruptions gracefully.

Key Variables:
    - INSTANCE_NAME: The display name for the instance to be launched.
    - COMPARTMENT_ID: The OCI compartment ID where the instance will be created.
    - SHAPE_NAME: The shape of the instance (e.g., VM.Standard.A1.Flex).
    - VCN_ID: The ID of the Virtual Cloud Network (VCN) in the compartment.
    - SUBNET_ID: The ID of the subnet within the VCN.
    - AD_NAMES: A list of availability domain names in the compartment.
    - SHAPE_CONFIG: Configuration details for the instance shape (OCPUs and memory).
    - AVAILABILITY_CONFIG: Configuration for instance recovery actions.
    - INSTANCE_OPTIONS: Options for the instance, such as disabling legacy IMDS endpoints.
    - METADATA: Metadata for the instance, including SSH authorized keys.
    - IMAGE_ID: The ID of the latest Ubuntu image matching the criteria.

Workflow:
    1. Load OCI configuration from the default file.
    2. Retrieve the list of availability domains, VCNs, and subnets in the compartment.
    3. Select the latest Ubuntu image (non-minimal, aarch64 architecture).
    4. Create a list of instance launch details for each availability domain.
    5. Attempt to launch instances in a loop, retrying on failure.
    6. Log errors to a file and handle specific error codes with appropriate delays.

Error Handling:
    - Retries on service errors with a delay (20s on 500 codes, 60s if anything else).
    - Logs error details to a file named "faillog.txt".
    - Gracefully exits on keyboard interruption (Ctrl+C).
"""

import oci
import os
from time import sleep
import sys


config = oci.config.from_file()
identity = oci.identity.IdentityClient(config)
compute_client = oci.core.ComputeClient(config)
network_client = oci.core.VirtualNetworkClient(config)


with open(os.path.expanduser(r"~/.ssh/id_rsa.pub"), "r") as f:
    pub_key = f.read()


INSTANCE_NAME = "Armz0"
COMPARTMENT_ID = config["tenancy"]
SHAPE_NAME = "VM.Standard.A1.Flex"
VCN_ID = network_client.list_vcns(compartment_id=COMPARTMENT_ID).data[0].id
SUBNET_ID = subnets = (
    network_client.list_subnets(compartment_id=COMPARTMENT_ID, vcn_id=VCN_ID).data[0].id
)
AD_NAMES = [
    ad.name
    for ad in identity.list_availability_domains(compartment_id=COMPARTMENT_ID).data
]
SHAPE_CONFIG = oci.core.models.LaunchInstanceShapeConfigDetails(
    ocpus=4, memory_in_gbs=24  # OCPUs  # GB of RAM
)
AVAILABILITY_CONFIG = oci.core.models.LaunchInstanceAvailabilityConfigDetails(
    recovery_action="RESTORE_INSTANCE"
)
INSTANCE_OPTIONS = oci.core.models.InstanceOptions(
    are_legacy_imds_endpoints_disabled=True
)
METADATA = {"ssh_authorized_keys": pub_key}

image_list = compute_client.list_images(
    compartment_id=COMPARTMENT_ID, shape=SHAPE_NAME
).data

ubuntu_list = []
for img in image_list:
    if (
        "Ubuntu" in img.display_name
        and "aarch64" in img.display_name
        and "Minimal" not in img.display_name
    ):
        ubuntu_list.append(img)
IMAGE_ID = sorted(ubuntu_list, key=lambda x: x.time_created, reverse=True)[0].id


def create_instance_list() -> list[oci.core.models.LaunchInstanceDetails]:
    """Create a list of instance detail objects to iterate over while trying to snag one of these"""
    instance_list = []

    for i in AD_NAMES:
        instance = oci.core.models.LaunchInstanceDetails(
            compartment_id=COMPARTMENT_ID,
            availability_domain=i,
            shape=SHAPE_NAME,
            shape_config=SHAPE_CONFIG,
            display_name=INSTANCE_NAME,
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image", image_id=IMAGE_ID
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=SUBNET_ID,
                assign_public_ip=True,
            ),
            metadata=METADATA,
            availability_config=AVAILABILITY_CONFIG,
            instance_options=INSTANCE_OPTIONS,
        )

        instance_list.append(instance)

    return instance_list


def safe_sleep(duration) -> None:
    """Using this to sleep and allow graceful keyboard interrupts without dumping errors to terminal"""
    try:
        sleep(duration)
    except KeyboardInterrupt:
        print("\nctrl-c  --  exiting")
        sys.exit(0)


def main():
    instance_list = create_instance_list()
    while True:
        for i in instance_list:
            try:
                response = compute_client.launch_instance(i)
                print("FINALLY!!!!")
                sys.exit(0)

            except oci.exceptions.ServiceError as e:
                err = e
                msg = "---".join(
                    [
                        err.timestamp,
                        i.availability_domain,
                        str(err.status),
                        err.message,
                    ]
                )
                print(msg)
                with open("faillog.txt", "a") as f:
                    f.write(f"{msg}\n")

                if err.status == 500:
                    safe_sleep(4)
                else:
                    safe_sleep(60)

            except KeyboardInterrupt:
                print("\nctrl-c  --  exiting")
                sys.exit(0)


if __name__ == "__main__":
    main()
