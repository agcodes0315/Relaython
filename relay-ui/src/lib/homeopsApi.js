export async function callBridgeTool(toolName, args = {}, endpoint = "/api/mcp/tool") {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool: toolName, arguments: args }),
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      payload?.error ||
      payload?.message ||
      `Relay bridge request failed (${response.status})`
    );
  }

  return payload;
}

export function createHomeOpsApi(callTool = callBridgeTool) {
  return {
    listAssets: () => callTool("list_household_assets", {}),

    getAsset: (assetId) =>
      callTool("get_household_asset", {
        asset_id: assetId,
      }),

    checkWarranty: (assetId) =>
      callTool("check_warranty", {
        asset_id: assetId,
      }),

    troubleshoot: (assetId, symptoms) =>
      callTool("troubleshoot_home_asset", {
        asset_id: assetId,
        symptoms,
      }),

    prepareService: (assetId, symptoms, constraints = {}) =>
      callTool("prepare_service_from_asset", {
        asset_id: assetId,
        symptoms,
        ...constraints,
      }),
  };
}
