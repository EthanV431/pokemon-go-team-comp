import { useState, useEffect } from 'react';
import { getImageUrl } from '../config/api';

function S3Image({ filename, alt = "", className = "", onError = null }) {
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!filename) {
      setLoading(false);
      return;
    }

    const loadImage = async () => {
      try {
        const url = await getImageUrl(filename);
        if (url) {
          setImageUrl(url);
        } else {
          setError(true);
          if (onError) onError();
        }
      } catch (err) {
        console.error('Error loading image:', err);
        setError(true);
        if (onError) onError();
      } finally {
        setLoading(false);
      }
    };

    loadImage();
  }, [filename, onError]);

  if (!filename || error) {
    return null; // Don't render anything if no filename or error
  }

  if (loading) {
    return <div className={className} style={{ minHeight: '50px', background: '#f0f0f0' }}></div>;
  }

  if (imageUrl) {
    return (
      <img 
        src={imageUrl} 
        alt={alt} 
        className={className}
        onError={() => {
          setError(true);
          if (onError) onError();
        }}
      />
    );
  }

  return null;
}

export default S3Image;
