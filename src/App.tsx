import { ThemeProvider, CssBaseline } from '@mui/material';
import { BrowserRouter } from 'react-router-dom';
import { theme } from './theme/theme';
import { AppRoutes } from './routes';
import { SimulationProvider } from './context/SimulationContext';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <SimulationProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </SimulationProvider>
    </ThemeProvider>
  );
}

export default App;
