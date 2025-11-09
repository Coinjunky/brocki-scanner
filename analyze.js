cat > netlify/functions/analyze.js <<'EOF'
exports.handler = async (event, context) => {

  // Handle CORS preflight requests
  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 200,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS"
      },
      body: "OK"
    };
  }

  // Parse JSON body safely
  let body = {};
  try {
    body = JSON.parse(event.body || "{}");
  } catch (err) {
    return {
      statusCode: 400,
      headers: { "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: "Invalid JSON" })
    };
  }

  // For now, just echo back the body
  return {
    statusCode: 200,
    headers: { "Access-Control-Allow-Origin": "*" },
    body: JSON.stringify({
      message: "Netlify analyze function working ✅",
      received: body
    })
  };
};
EOF
