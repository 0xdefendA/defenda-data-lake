FROM public.ecr.aws/sam/build-python3.13:latest

ENV AWS_DEFAULT_REGION us-west-2

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN mkdir /asset-input
WORKDIR /asset-input
ADD . .

# Install only the dependencies the lambdas actually need.
# boto3/botocore/s3transfer/jmespath are provided by the Lambda runtime
# so we exclude them to keep the zip small (~75MB savings from botocore alone).
# pandas/numpy are NOT needed at lambda runtime.
RUN uv pip install --no-cache \
    chevron \
    fsspec \
    netaddr \
    python-dateutil \
    pyyaml \
    tenacity \
    tzlocal \
    --target /asset-output

# Install pyathena without deps to avoid pulling in pandas/numpy.
# It only needs boto3 + fsspec + tenacity for the cursor pattern
# used in generate_partitions.py — boto3 comes from the Lambda runtime,
# fsspec and tenacity are installed above.
RUN uv pip install --no-cache --no-deps \
    pyathena \
    --target /asset-output

# Copy source files to output
RUN rsync -r --exclude='Dockerfile' --exclude='requirements.txt' --exclude='.dockerignore' --exclude='tests' . /asset-output

WORKDIR /asset-output
RUN zip -9yr lambda.zip .
