import express from "express";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 10000;

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "OK" });
});

// Root
app.get("/", (req, res) => {
  res.send("Brocki Scanner API ✅");
});

// Product search route (already existing)
app.post("/api/search", (req, res) => {
  console.log("POST /api/search body:", req.body);

  const query = req.body.query || "none";

  res.json({
    success: true,
    message: "Search completed",
    query
  });
});

// New image analyze route
app.post("/analyze", (req, res) => {
  console.log("POST /analyze:", req.body);

  // Simulated response
  res.json({
    success: true,
    message: "Image analyzed successfully ✅",
    data: {
      detected: "Example category",
      confidence: 0.87
    }
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
