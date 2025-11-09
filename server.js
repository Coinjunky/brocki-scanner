const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
app.use(cors()); // allow cross-origin requests
app.use(bodyParser.json({ limit: '10mb' })); // for large images

app.get('/health', (req, res) => res.json({ message: "Brocki Scanner API is alive!" }));

app.post('/analyze', (req, res) => {
    const { image, query } = req.body;
    // do your AI/image processing here
    res.json({ recognition: { product_name: "Sample Product", labels: ["tag1", "tag2"] }, stats: {} });
});

app.post('/search', (req, res) => {
    const { query } = req.body;
    // do your product search here
    res.json({ listings: {}, stats: {} });
});

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Server running on port ${port}`));
