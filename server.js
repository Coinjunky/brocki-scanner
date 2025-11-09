const express = require('express');
const cors = require('cors');

const app = express();

// **CORS aktivieren**
app.use(cors());

// Body-Parser (für POST-Anfragen)
app.use(express.json());

app.get('/', (req, res) => {
  res.send('Backend läuft');
});

// Beispiel Analyze-Route
app.post('/analyze', (req, res) => {
  const { image, query } = req.body;
  // hier Analyse-Code
  res.json({ success: true, message: 'Analyze funktioniert!' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server läuft auf Port ${PORT}`));
