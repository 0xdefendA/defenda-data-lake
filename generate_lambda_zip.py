#!/usr/bin/env python
import docker
from os import path
import subprocess


def refresh_requirements():
    subprocess.Popen(
        "pipenv run pip freeze > lambdas/requirements.txt",
        shell=True,
        stdout=subprocess.PIPE,
    ).stdout.read()


def build_lambda_image():
    docker_client = docker.from_env()
    docker_client.images.build(path="lambdas/", tag="datalake-lambdas", quiet=False)


def get_lambda_zip():
    docker_client = docker.from_env()
    docker_client.containers.run(
        "datalake-lambdas",
        "cp /asset-output/lambda.zip /mnt/cdk-data-lake/lambdas",
        volumes={
            path.abspath("."): {
                "bind": "/mnt/cdk-data-lake",
                "mode": "rw",
            }
        },
        remove=True,
    )


if __name__ == "__main__":
    print("refreshing requirements.txt using pipenv")
    refresh_requirements()
    print("Building image with requirements.txt")
    build_lambda_image()
    print("Retrieving zip file for lambda")
    get_lambda_zip()
