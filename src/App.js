import GiovanniDataDisplay from './components/GiovanniDataDisplay';
import ArloDataDisplay from './components/ArloDataDisplay';
import CliffDataDisplay from './components/CliffDataDisplay';
import SierraDataDisplay from './components/SierraDataDisplay';
import MainMenu from './components/MainMenu';
import './App.css';
import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<MainMenu />} />
        <Route path="/giovanni" element={<GiovanniDataDisplay />} />
        <Route path="/arlo" element={<ArloDataDisplay />} />
        <Route path="/cliff" element={<CliffDataDisplay />} />
        <Route path="/sierra" element={<SierraDataDisplay />} />
      </Routes>
    </div>
  );
}

export default App;