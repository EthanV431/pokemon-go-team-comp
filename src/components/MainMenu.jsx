import { Link } from 'react-router-dom';
import styles from './DataDisplay.module.css';
import pokeball from '../images/pokeball.png';

function MainMenu () {
  return (
    <div className={styles.mainMenu}>
      <div className={styles.mainMenuTitleSection}>
        <h1>Welcome to Pokémon GO Team Comp</h1>
        <p>Select an option from the menu to get started.</p>
      </div>
      <div className={styles.mainMenuButtonContainer}>
        <Link to="/giovanni">
          <button className={styles.mainMenuButton}>
            <img src={pokeball} alt="" className={styles.pokeballIcon} />
            Giovanni Counters
          </button>
        </Link>
        <Link to="/arlo">
          <button className={styles.mainMenuButton}>
            <img src={pokeball} alt="" className={styles.pokeballIcon} />
            Arlo Counters
          </button>
        </Link>
        <Link to="/cliff">
          <button className={styles.mainMenuButton}>
            <img src={pokeball} alt="" className={styles.pokeballIcon} />
            Cliff Counters
          </button>
        </Link>
        <Link to="/sierra">
          <button className={styles.mainMenuButton}>
            <img src={pokeball} alt="" className={styles.pokeballIcon} />
            Sierra Counters
          </button>
        </Link>
      </div>
    </div>
  );
}

export default MainMenu;