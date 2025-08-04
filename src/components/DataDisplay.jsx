import { useState, useEffect } from 'react';
import styles from './DataDisplay.module.css'

function DataDisplay() {
  const [rows, setRows] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState('');

    useEffect(() => {
    fetch('http://localhost:5000/api/data')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(json => {
        setRows(json.rows || []);
        setHeaders(json.headers || []);
        setTitle(json.title || '');
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (error)  return <div>Error: {error}</div>;
  if (loading) return <div>Loading…</div>;

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.titleWrapper}>
        <h1>{title}</h1>
      </div>
      <div className={styles.tableWrapper}>
        {headers.map((hdr, colIndex) => {
          const splitRows = rows.map(row => row[colIndex].split('\n'));
          const numCols = Math.max(...splitRows.map(seg => seg.length), 1);

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
              </thead>
              <tbody>
                {splitRows.map((segments, rowIndex) => (
                  <tr key={rowIndex}>
                    {segments.map((text, segIdx) => (
                      <td key={segIdx} className={styles.bodyCell}>
                        {text}
                      </td>
                    ))}
                    {Array.from({ length: numCols - segments.length }).map((_, padIdx) => (
                      <td key={`pad-${padIdx}`} className={styles.bodyCell}></td>
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

export default DataDisplay;