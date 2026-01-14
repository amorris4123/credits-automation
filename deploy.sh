#!/bin/bash
###############################################################################
# CreditBot Deployment Script
# Builds Docker image and pushes to AWS ECR
#
# Usage:
#   ./deploy.sh [version]
#
# Examples:
#   ./deploy.sh            # Deploy as 'latest'
#   ./deploy.sh v1.0.0     # Deploy with specific version tag
#
# Prerequisites:
#   - AWS CLI configured with access to accsec-prod-twilio
#   - Docker installed and running
#   - ECR repository created: accsec-ai/credit-bot
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-""}  # Set this or get from AWS CLI
ECR_REPOSITORY="accsec-ai/credit-bot"
IMAGE_NAME="credit-bot"

# Get version from argument or default to 'latest'
VERSION=${1:-latest}

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi

    # Get AWS account ID if not set
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            print_error "Could not determine AWS Account ID. Set AWS_ACCOUNT_ID environment variable."
            exit 1
        fi
    fi

    print_info "Prerequisites check passed ✓"
    print_info "AWS Account ID: $AWS_ACCOUNT_ID"
    print_info "AWS Region: $AWS_REGION"
}

authenticate_ecr() {
    print_info "Authenticating with ECR..."

    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

    if [ $? -eq 0 ]; then
        print_info "ECR authentication successful ✓"
    else
        print_error "ECR authentication failed"
        exit 1
    fi
}

build_image() {
    print_info "Building Docker image..."
    print_info "Image: $IMAGE_NAME:$VERSION"

    docker build -t $IMAGE_NAME:$VERSION .

    if [ $? -eq 0 ]; then
        print_info "Docker build successful ✓"
    else
        print_error "Docker build failed"
        exit 1
    fi
}

tag_image() {
    print_info "Tagging image for ECR..."

    ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

    # Tag with version
    docker tag $IMAGE_NAME:$VERSION $ECR_URL:$VERSION
    print_info "Tagged as: $ECR_URL:$VERSION"

    # Also tag as latest if this is a version release
    if [ "$VERSION" != "latest" ]; then
        docker tag $IMAGE_NAME:$VERSION $ECR_URL:latest
        print_info "Tagged as: $ECR_URL:latest"
    fi
}

push_image() {
    print_info "Pushing image to ECR..."

    ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

    # Push version tag
    docker push $ECR_URL:$VERSION

    if [ $? -eq 0 ]; then
        print_info "Pushed: $ECR_URL:$VERSION ✓"
    else
        print_error "Failed to push image"
        exit 1
    fi

    # Also push latest tag if applicable
    if [ "$VERSION" != "latest" ]; then
        docker push $ECR_URL:latest
        if [ $? -eq 0 ]; then
            print_info "Pushed: $ECR_URL:latest ✓"
        fi
    fi
}

print_next_steps() {
    print_info "==========================================="
    print_info "Deployment Complete! ✓"
    print_info "==========================================="
    echo ""
    print_info "Next steps:"
    echo "  1. Update Airflow DAG with the new image:"
    echo "     image='${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${VERSION}'"
    echo ""
    echo "  2. Deploy DAG to airflow-dags repository:"
    echo "     cp airflow/credit_bot_dag.py <airflow-dags-repo>/dags/credit_bot/"
    echo ""
    echo "  3. Verify deployment in Airflow UI:"
    echo "     https://airflow.accsec-ai.mwaa.amazonaws.com"
    echo ""
    echo "  4. Monitor first execution:"
    echo "     - Check DAG appears in UI"
    echo "     - Manually trigger test run"
    echo "     - Review logs"
    echo ""
}

# Main execution
main() {
    echo "==========================================="
    echo "CreditBot Deployment Script"
    echo "==========================================="
    echo ""

    check_prerequisites
    authenticate_ecr
    build_image
    tag_image
    push_image
    print_next_steps
}

# Run main function
main
