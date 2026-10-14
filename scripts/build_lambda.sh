#!/usr/bin/env bash
#
# Build (and optionally deploy) the Relay resume Lambda.
#
#   bash scripts/build_lambda.sh             build only -> build/relay_resume_worker.zip
#   DEPLOY=1 bash scripts/build_lambda.sh    build, then upload to AWS
#
# Works on macOS (bash 3.2) and Linux. handler.py ends up at the TOP LEVEL of
# the zip, so the Lambda handler setting in AWS must be: handler.lambda_handler
#
# Optional settings (all have defaults):
#   RELAY_RESUME_LAMBDA   function name   (default RelayResumeWorker)
#   RELAY_DEPLOY_REGION   AWS region      (default us-west-2)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/lambda/resume_worker/handler.py"
BUILD_DIR="$REPO_ROOT/build"
ZIP_FILE="$BUILD_DIR/relay_resume_worker.zip"
FUNCTION_NAME="${RELAY_RESUME_LAMBDA:-RelayResumeWorker}"
REGION="${RELAY_DEPLOY_REGION:-us-west-2}"
EXPECTED_HANDLER="handler.lambda_handler"

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: cannot find $SOURCE" >&2
  exit 1
fi

# The Lambda is deployed as ONE file, so it must not import the relay package.
if grep -nE '^[[:space:]]*(from|import)[[:space:]]+relay([[:space:].]|$)' "$SOURCE"; then
  echo "ERROR: handler.py imports 'relay'. It must stay standalone." >&2
  exit 1
fi

mkdir -p "$BUILD_DIR"
rm -f "$ZIP_FILE"

if command -v zip >/dev/null 2>&1; then
  # -j keeps only the file name, so handler.py sits at the zip root.
  zip -j -X -q "$ZIP_FILE" "$SOURCE"
else
  echo "zip not found, using python3 instead"
  python3 - "$SOURCE" "$ZIP_FILE" <<'PY'
import sys
import zipfile

source, target = sys.argv[1], sys.argv[2]

with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.write(source, "handler.py")
PY
fi

echo "Built: $ZIP_FILE"

if command -v unzip >/dev/null 2>&1; then
  unzip -l "$ZIP_FILE"
fi

if [ "${DEPLOY:-0}" = "1" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: DEPLOY=1 needs the AWS CLI (aws) on your PATH." >&2
    exit 1
  fi

  echo "Deploying to $FUNCTION_NAME in $REGION ..."

  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$REGION"

  aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION"

  CURRENT_HANDLER="$(aws lambda get-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --query Handler \
    --output text)"

  if [ "$CURRENT_HANDLER" != "$EXPECTED_HANDLER" ]; then
    echo
    echo "WARNING: the Lambda handler setting is '$CURRENT_HANDLER'."
    echo "         The new zip needs '$EXPECTED_HANDLER'. Fix it with:"
    echo "  aws lambda update-function-configuration --function-name $FUNCTION_NAME --handler $EXPECTED_HANDLER --region $REGION"
  fi

  echo "Deployed."
else
  echo "(Build only. Set DEPLOY=1 to upload it.)"
fi

echo
echo "REMINDER: the Lambda handler setting in AWS must be: $EXPECTED_HANDLER"