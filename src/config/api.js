export const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000/api';

// Add function to handle S3 image URLs
export const getImageUrl = async (filename) => {
  try {
    const response = await fetch(`${API_BASE}/images/${filename}`);
    const data = await response.json();
    return data.image_url || null;
  } catch (error) {
    console.error('Error fetching image URL:', error);
    return null;
  }
};