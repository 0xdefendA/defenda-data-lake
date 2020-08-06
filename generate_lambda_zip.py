import docker
from os import path


def build_processor_image():
    docker_client = docker.from_env()
    docker_client.images.build(path="firehose-processor/", tag="processor", quiet=False)


def get_processor_zip():
    docker_client = docker.from_env()
    docker_client.containers.run(
        "processor",
        "cp /asset-output/lambda.zip /mnt/cdk-data-lake/firehose-processor",
        volumes={path.abspath("."): {"bind": "/mnt/cdk-data-lake", "mode": "rw",}},
    )


if __name__ == "__main__":
    print("Building image with requirements.txt")
    build_processor_image()
    print("Retrieving zip file for lambda")
    get_processor_zip()
