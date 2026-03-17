import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';
import { Home } from './pages/Home';
import { Visualizer } from './pages/Visualizer';

axios.defaults.baseURL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-white">
        <header className="p-6 flex items-center justify-between border-b border-gray-100">
          <div className="flex items-center space-x-2">
            <Link to="/" className="flex items-center space-x-2">
              <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-sm">
                R
              </div>
              <span className="text-xl font-medium text-gray-700 tracking-tight">ragcli</span>
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            <Link
              to="/visualize"
              className="text-sm text-gray-600 hover:text-primary-600 transition-colors font-medium"
            >
              Vector Graph
            </Link>
            <div className="h-2 w-2 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-500">System Ready</span>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/visualize" element={<Visualizer />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
