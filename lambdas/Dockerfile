FROM public.ecr.aws/sam/build-python3.13:latest

ENV AWS_DEFAULT_REGION us-west-2

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN mkdir /asset-input
WORKDIR /asset-input
ADD . .

# Install dependencies into the output directory using uv
RUN uv pip install --no-cache \
    boto3 \
    chevron \
    netaddr \
    pandas \
    pyathena \
    python-dateutil \
    pyyaml \
    tzlocal \
    --target /asset-output

# Copy source files to output
RUN rsync -r --exclude='Dockerfile' --exclude='requirements.txt' --exclude='.dockerignore' --exclude='tests' . /asset-output

WORKDIR /asset-output
RUN zip -9yr lambda.zip .
