import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styles from './DataDisplay.module.css'

function CliffDataDisplay() {
  const [rows, setRows] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');

    useEffect(() => {
    fetch('http://localhost:5000/api/cliffTeam')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(json => {
        setRows(json.rows || []);
        setHeaders(json.headers || []);
        setTitle(json.title || '');
        setLastUpdated(json.last_updated || '');
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
              Main Menu
            </button>
          </Link>
          <Link to="/giovanni">
            <button className={styles.navButton}>
              Giovanni
            </button>
          </Link>
          <Link to="/arlo">
            <button className={styles.navButton}>
              Arlo
            </button>
          </Link>
          <Link to="/sierra">
            <button className={styles.navButton}>
              Sierra
            </button>
          </Link>
        </div>
      </div>
      <div className={styles.tableWrapper}>
        {headers.map((hdr, colIndex) => {
            const splitRows = rows.map(row => {
            const cell = row[colIndex] || "";
            const [col1 = "", rest = ""] = cell.split('\n');
            const [col2 = "", col3 = ""] = rest
            .split(',')
            .map(s => s.trim());
            return [col1.trim(), col2, col3];
        });
        const numCols = 3;

          return (
            <table key={colIndex} className={styles.table}>
              <thead>
                <tr>
                  <th
                    className={styles.headerCell}
                    colSpan={numCols}
                  >
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
                {splitRows.map((segments, rowIndex) => (
                  <tr key={rowIndex}>
                    {segments.map((text, segIdx) => (
                      <td key={segIdx} className={styles.bodyCell}>
                        {text}
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

export default CliffDataDisplay;