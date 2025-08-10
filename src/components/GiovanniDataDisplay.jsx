import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styles from './DataDisplay.module.css';
import pokeball from '../images/pokeball.png';
import { API_BASE } from '../config/api';
import S3Image from './S3Image';

function GiovanniDataDisplay() {
  const [rows, setRows] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');
  const [headerImages, setHeaderImages] = useState([]);
  const [bodyImages, setBodyImages] = useState([]);

    useEffect(() => {
    fetch(`${API_BASE}/giovanniTeam`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(json => {
        setRows(json.rows || []);
        setHeaders(json.headers || []);
        setTitle(json.title || '');
        setLastUpdated(json.last_updated || '');
        // Slice header images to match headers length
        const headerImgs = json.header_images || [];
        const headersLength = (json.headers || []).length;
        setHeaderImages(headerImgs.slice(0, headersLength));
        // Slice body images to match headers length
        const bodyImgs = (json.body_images || []).map(row => row.slice(0, headersLength));
        setBodyImages(bodyImgs);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const formatLastUpdated = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  if (error)  return <div>Error: {error}</div>;
  if (loading) return <div>Loading…</div>;

  return (
      <div className={styles.pageWrapper}>
        <div className={styles.titleWrapper}>
          <h1>{title}</h1>
          {lastUpdated && (
              <p className={styles.lastUpdated}>
              Last updated: {formatLastUpdated(lastUpdated)}
              </p>
          )}
          <div className={styles.navigationButtons}>
            <Link to="/">
              <button className={styles.navButton}>
                <img src={pokeball} alt="" className={styles.pokeballIcon} />
                Main Menu
              </button>
            </Link>
            <Link to="/giovanni">
              <button className={styles.navButton}>
                <img src={pokeball} alt="" className={styles.pokeballIcon} />
                Giovanni
              </button>
            </Link>
            <Link to="/arlo">
              <button className={styles.navButton}>
                <img src={pokeball} alt="" className={styles.pokeballIcon} />
                Arlo
              </button>
            </Link>
            <Link to="/cliff">
              <button className={styles.navButton}>
                <img src={pokeball} alt="" className={styles.pokeballIcon} />
                Cliff
              </button>
            </Link>
            <Link to="/sierra">
              <button className={styles.navButton}>
                <img src={pokeball} alt="" className={styles.pokeballIcon} />
                Sierra
              </button>
            </Link>
          </div>
        </div>
        <div className={styles.tableWrapper}>
          <div className={styles.description}>
            <h3>Giovanni is the boss of Team GO Rocket. He always leads with the first Pokémon on this page.</h3>
          </div>
          <div className={styles.subtitle}>
            <h2>Giovanni's Pokémon</h2>
            <h3>These are the Pokémon Giovanni uses in his current lineup with reccommendations to beat them. <br />If you don't have Mega or Shadow versions of these Pokémon, regular versions can still be effective.</h3>
            <h3>Note that Giovanni's Pokémon may change in the future, so this data may not always be accurate.</h3>
            <h3>For the latest information, please refer to the official Pokémon GO website or community resources.</h3>
          </div>
          {headers.map((hdr, colIndex) => {
            const splitRows = rows.map((row, originalRowIndex) => {
              const cell = row[colIndex] || "";
              const [col1 = "", rest = ""] = cell.split('\n');
              const [col2 = "", col3 = ""] = rest
              .split(',')
              .map(s => s.trim());
              return {
                segments: [col1.trim(), col2, col3],
                originalIndex: originalRowIndex
              };
            }).filter(item => item.segments.some(text => text && text.trim() !== ""));
            const numCols = 3;

            return (
              <table key={colIndex} className={styles.table}>
                <thead>
                  <tr>
                    <th
                      className={styles.headerCell}
                      colSpan={numCols}
                    >
                      {headerImages[colIndex] && (
                        <S3Image 
                          filename={headerImages[colIndex]} 
                          alt="" 
                          className={styles.headerImage}
                        />
                      )}
                      {hdr}
                    </th>
                  </tr>
                  <tr>
                      <th className={styles.headerCell}>Pokémon</th>
                      <th className={styles.headerCell}>Fast Move</th>
                      <th className={styles.headerCell}>Charged Move</th>
                  </tr>
                </thead>
                <tbody>
                  {splitRows.map((item, filteredRowIndex) => (
                    <tr key={filteredRowIndex}>
                      {item.segments.map((text, segIdx) => (
                        <td key={segIdx} className={styles.bodyCell}>
                          <div className={styles.cellContent}>
                            {segIdx === 0 && bodyImages[item.originalIndex] && bodyImages[item.originalIndex][colIndex] && (
                              <S3Image 
                                filename={bodyImages[item.originalIndex][colIndex]} 
                                alt="" 
                                className={styles.rowImage}
                              />
                            )}
                            <span>{text}</span>
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })}
        </div>
      </div>
    );
  }

export default GiovanniDataDisplay;