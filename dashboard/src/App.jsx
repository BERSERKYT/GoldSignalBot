import React from 'react'
import Header from './components/Header'
import ActiveSignal from './components/ActiveSignal'
import Charts from './components/Charts'
import PerformanceMetrics from './components/PerformanceMetrics'
import RecentSignals from './components/RecentSignals'

function App() {
  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex flex-col">
      <Header />
      
      <main className="max-w-[1600px] mx-auto w-full p-4 md:p-6 flex flex-col gap-4 md:gap-6 flex-1">
        <div className="grid grid-cols-12 gap-4 md:gap-6">
          
          {/* Main Content Area (Center-Left) */}
          <div className="col-span-12 lg:col-span-9 flex flex-col gap-6">
            <ActiveSignal />
            <Charts />
            <PerformanceMetrics />
          </div>

          {/* Right Sidebar */}
          <RecentSignals />
          
        </div>
      </main>

      <footer className="mt-auto p-6 border-t border-slate-200 dark:border-slate-800 text-slate-500 text-[10px] font-medium tracking-widest uppercase">
          <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="flex items-center gap-8">
                  <span>API Status: <span className="text-success">Connected</span></span>
                  <span>Server Load: <span className="text-success">12%</span></span>
                  <span>Latency: <span className="text-success">14ms</span></span>
              </div>
              <div className="flex items-center gap-6">
                  <a className="hover:text-primary" href="#">Terms of Service</a>
                  <a className="hover:text-primary" href="#">Risk Disclosure</a>
                  <a className="hover:text-primary" href="#">Help Center</a>
                  <span className="text-slate-400">© 2024 GoldSignalBot AI</span>
              </div>
          </div>
      </footer>
    </div>
  )
}

export default App
