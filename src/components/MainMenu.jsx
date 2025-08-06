import { Link } from 'react-router-dom';
import styles from './DataDisplay.module.css';

function MainMenu () {
  return (
    <div className={styles.mainMenu}>
      <h1>Welcome to Pokémon GO Team Comp</h1>
      <p>Select an option from the menu to get started.</p>
      <div className={styles.mainMenuButtonContainer}>
        <Link to="/giovanni">
          <button className={styles.mainMenuButton}>
            Giovanni Counters
          </button>
        </Link>
        <Link to="/arlo">
          <button className={styles.mainMenuButton}>
            Arlo Counters
          </button>
        </Link>
        <Link to="/cliff">
          <button className={styles.mainMenuButton}>
            Cliff Counters
          </button>
        </Link>
        <Link to="/sierra">
          <button className={styles.mainMenuButton}>
            Sierra Counters
          </button>
        </Link>
      </div>
    </div>
  );
}

export default MainMenu;