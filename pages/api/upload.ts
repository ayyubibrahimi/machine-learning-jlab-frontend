import type { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';
import FormData from 'form-data';
import multer from 'multer';

const CLOUD_FUNCTION_URL = process.env.NEXT_PRIVATE_CLOUD_FUNCTION_API_KEY;

const upload = multer({
  storage: multer.memoryStorage(),
});

export const config = {
  api: {
    bodyParser: false,
  },
};

const uploadMiddleware = upload.fields([
  { name: 'files', maxCount: 10 },
  { name: 'script', maxCount: 1 },
  { name: 'model', maxCount: 1 },
  { name: 'custom_template', maxCount: 1 },
  { name: 'send_email', maxCount: 1 },
  { name: 'user_email', maxCount: 1 }
]);

const handler = async (req: NextApiRequest, res: NextApiResponse) => {
  if (!CLOUD_FUNCTION_URL) {
    console.error('CLOUD_FUNCTION_URL is not set');
    return res.status(500).json({ error: 'Server configuration error' });
  }

  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }

  uploadMiddleware(req as any, res as any, async (err: any) => {
    if (err) {
      console.error('File upload error:', err);
      return res.status(500).json({ error: 'File upload failed' });
    }

    const files = (req as any).files?.['files'] as Express.Multer.File[];
    if (!files || files.length === 0) {
      return res.status(400).json({ error: 'No files uploaded' });
    }

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file.buffer, file.originalname);
    });

    const fields = ['script', 'model', 'custom_template', 'send_email', 'user_email'];
    fields.forEach(field => {
      const value = (req as any).body[field] || (req as any).files?.[field]?.[0]?.buffer;
      if (value) {
        formData.append(field, value);
      }
    });

    try {
      const response = await axios.post(CLOUD_FUNCTION_URL, formData, {
        headers: {
          ...formData.getHeaders(),
        },
      });
      return res.status(response.status).json(response.data);
    } catch (error) {
      console.error('Error uploading files:', error);
      return res.status(500).json({ error: 'File upload to Cloud Function failed' });
    }
  });
};

export default handler;