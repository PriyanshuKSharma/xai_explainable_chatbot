import { useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, AreaChart, Area
} from 'recharts';
import { 
  LayoutDashboard, Server, ShieldCheck, Activity, Terminal, PlayCircle, Zap, FileText, Download
} from 'lucide-react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { Document, Packer, Paragraph, ImageRun } from 'docx';
import { saveAs } from 'file-saver';

const mockMetrics = [
  { name: 'Jan', requests: 4000, accuracy: 84 },
  { name: 'Feb', requests: 3000, accuracy: 86 },
  { name: 'Mar', requests: 5000, accuracy: 89 },
  { name: 'Apr', requests: 8000, accuracy: 92 },
  { name: 'May', requests: 7500, accuracy: 93 },
  { name: 'Jun', requests: 9000, accuracy: 94 },
];

const mockStockData = [
  { time: '09:30', price: 150.2 },
  { time: '11:00', price: 153.1 },
  { time: '13:00', price: 152.8 },
  { time: '14:30', price: 156.4 },
  { time: '16:00', price: 157.9 },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [chartType, setChartType] = useState('Area');

  const handleExportPDF = async () => {
    const element = document.getElementById('dashboard-canvas');
    if (!element) return;
    const canvas = await html2canvas(element, { scale: 2, backgroundColor: '#0a0a0f' });
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('l', 'pt', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save('XAI_Analytics_Report.pdf');
  };

  const handleExportDOCX = async () => {
    const element = document.getElementById('dashboard-canvas');
    if (!element) return;
    const canvas = await html2canvas(element, { scale: 1, backgroundColor: '#0a0a0f' });
    const imgData = canvas.toDataURL('image/png');
    // Transform data URL to Uint8Array for docx
    const res = await fetch(imgData);
    const blob = await res.blob();
    const arrayBuffer = await blob.arrayBuffer();

    const doc = new Document({
      sections: [{
        properties: {},
        children: [
          new Paragraph({
            children: [
              new ImageRun({
                data: arrayBuffer,
                transformation: { width: 600, height: (canvas.height * 600) / canvas.width },
                type: 'png'
              } as any)
            ]
          })
        ]
      }]
    });
    const docBlob = await Packer.toBlob(doc);
    saveAs(docBlob, 'XAI_Analytics_Report.docx');
  };

  const renderSelectedChart = (data: any, dataKey: string, strokeColor: string, isGradient: boolean) => {
    if (chartType === 'Area') {
      return (
        <AreaChart data={data}>
          {isGradient && (
            <defs>
              <linearGradient id="colorGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={strokeColor} stopOpacity={0}/>
              </linearGradient>
            </defs>
          )}
          <XAxis dataKey="name" stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#fff'}} />
          <Area type="monotone" dataKey={dataKey} stroke={strokeColor} strokeWidth={3} fillOpacity={isGradient ? 1 : 0.3} fill={isGradient ? "url(#colorGrad)" : strokeColor} />
        </AreaChart>
      );
    }
    if (chartType === 'Bar') {
      return (
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis dataKey="name" stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#fff'}} cursor={{fill: '#1e293b'}} />
          <Bar dataKey={dataKey} fill={strokeColor} radius={[4, 4, 0, 0]} />
        </BarChart>
      );
    }
    return (
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey={data[0]?.name ? Object.keys(data[0])[0] : "time"} stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
        <YAxis stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#fff'}} />
        <Line type="monotone" dataKey={dataKey} stroke={strokeColor} strokeWidth={3} dot={{ fill: strokeColor, strokeWidth: 2 }} activeDot={{ r: 8 }} />
      </LineChart>
    );
  };

  return (
    <div className="flex h-screen bg-black text-slate-200 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-[#0a0a0f] flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="p-2 bg-cyan-500/10 rounded-lg">
            <Zap className="text-cyan-400 w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">
            XAI Analytics
          </h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          <button 
            onClick={() => setActiveTab('overview')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'overview' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'hover:bg-slate-800/50 text-slate-400'}`}
          >
            <LayoutDashboard className="w-5 h-5" />
            <span className="font-medium">Overview</span>
          </button>
          <button 
            onClick={() => setActiveTab('models')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'models' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'hover:bg-slate-800/50 text-slate-400'}`}
          >
            <Activity className="w-5 h-5" />
            <span className="font-medium">ML Models</span>
          </button>
          <button 
            onClick={() => setActiveTab('system')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'system' ? 'bg-pink-500/10 text-pink-400 border border-pink-500/20' : 'hover:bg-slate-800/50 text-slate-400'}`}
          >
            <Server className="w-5 h-5" />
            <span className="font-medium">System Status</span>
          </button>
        </nav>

        <div className="p-6 mt-auto">
          <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/50 backdrop-blur-md">
            <div className="flex items-center gap-2 text-sm text-emerald-400 mb-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Engine Online
            </div>
            <p className="text-xs text-slate-500">FastAPI backend is running optimally.</p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-y-auto">
        {/* Top Navbar */}
        <header className="h-20 border-b border-slate-800 flex items-center justify-between px-8 bg-black/50 backdrop-blur-xl sticky top-0 z-50">
          <div className="flex items-center gap-6">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white capitalize">{activeTab} Metrics</h2>
              <p className="text-sm text-slate-400">Live operational telemetry mapped in real-time.</p>
            </div>
            <div className="flex items-center gap-2 ml-4">
               <span className="text-xs font-medium text-slate-500">Chart Type:</span>
               <select 
                 className="bg-slate-800 border border-slate-700 text-sm rounded-lg px-3 py-1.5 outline-none focus:border-cyan-500 text-slate-300"
                 value={chartType}
                 onChange={(e) => setChartType(e.target.value)}
               >
                 <option value="Area">Area Fill</option>
                 <option value="Line">Line</option>
                 <option value="Bar">Bar</option>
               </select>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={handleExportDOCX} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-blue-400 rounded-lg text-sm font-medium transition-colors border border-blue-500/20">
              <FileText className="w-4 h-4" />
              DOCX
            </button>
            <button onClick={handleExportPDF} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-red-400 rounded-lg text-sm font-medium transition-colors border border-red-500/20">
              <Download className="w-4 h-4" />
              PDF
            </button>
            <div className="h-6 w-px bg-slate-800 mx-2"></div>
            <a href="https://nyayafinanceai.streamlit.app/" target="_blank" rel="noreferrer" className="flex items-center gap-2 px-5 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm font-semibold transition-all shadow-[0_0_15px_rgba(34,211,238,0.4)] text-white">
              <PlayCircle className="w-4 h-4" />
              App
            </a>
          </div>
        </header>

        {/* Dashboard Canvas wrapped for HTMl2Canvas Exports */}
        <div id="dashboard-canvas" className="p-8 pb-32">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Stat Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {[
                  { title: "Total Inferences", value: "84,029", trend: "+12.5%", color: "text-cyan-400" },
                  { title: "Avg Latency", value: "114ms", trend: "-5.2%", color: "text-emerald-400" },
                  { title: "XAI Hit Rate", value: "98.1%", trend: "+1.1%", color: "text-indigo-400" },
                  { title: "Active Threads", value: "12", trend: "0.0%", color: "text-slate-400" },
                ].map((stat, i) => (
                  <div key={i} className="bg-[#0f172aa6] border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                       <Activity className="w-16 h-16" />
                    </div>
                    <p className="text-sm font-medium text-slate-400 mb-2">{stat.title}</p>
                    <h3 className="text-3xl font-bold text-white tracking-tight">{stat.value}</h3>
                    <div className="mt-4 text-xs font-semibold tracking-wide" style={{color: stat.trend.startsWith('+') ? '#34d399' : '#94a3b8'}}>
                      {stat.trend} vs last month
                    </div>
                  </div>
                ))}
              </div>

              {/* Charts grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
                <div className="bg-[#0f172aa6] border border-slate-800 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-white mb-6">Traffic Volume (Conversations)</h3>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      {renderSelectedChart(mockMetrics, "requests", "#22d3ee", true)}
                    </ResponsiveContainer>
                  </div>
                </div>
                
                <div className="bg-[#0f172aa6] border border-slate-800 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-white mb-6">Live Stock Endpoint Ping (AAPL)</h3>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      {renderSelectedChart(mockStockData, "price", "#818cf8", false)}
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'models' && (
            <div className="space-y-6">
              <div className="bg-gradient-to-br from-indigo-900/40 to-[#0f172aa6] border border-indigo-500/20 rounded-2xl p-8 backdrop-blur-md">
                <div className="flex items-center gap-4 mb-4">
                  <div className="p-3 bg-indigo-500/20 rounded-xl">
                    <ShieldCheck className="w-8 h-8 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">Loan Fallback XAI Predictor</h2>
                    <p className="text-indigo-200/60 mt-1">Random Forest Ensemble vs Rule-based Heuristics Status</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
                  <div className="space-y-4">
                     <div className="flex justify-between text-sm">
                       <span className="text-slate-400">Model Accuracy (Pickled)</span>
                       <span className="text-indigo-400 font-bold">94.5%</span>
                     </div>
                     <div className="w-full bg-slate-800 rounded-full h-2">
                        <div className="bg-indigo-500 h-2 rounded-full" style={{ width: '94.5%' }}></div>
                     </div>
                     
                     <div className="flex justify-between text-sm pt-4">
                       <span className="text-slate-400">Fallback Heuristic Hit Rate</span>
                       <span className="text-pink-400 font-bold">100%</span>
                     </div>
                     <div className="w-full bg-slate-800 rounded-full h-2">
                        <div className="bg-pink-500 h-2 rounded-full" style={{ width: '100%' }}></div>
                     </div>
                  </div>
                  
                  <div className="bg-black/40 rounded-xl p-5 border border-slate-700 font-mono text-xs text-indigo-300">
                     <p className="mb-2 text-indigo-400">{"// Fallback Logic Engine State"}</p>
                     <p>{"{"}</p>
                     <p className="pl-4">"threshold_dti": 0.40,</p>
                     <p className="pl-4">"threshold_credit": 650,</p>
                     <p className="pl-4">"xai_engine_active": true,</p>
                     <p className="pl-4 text-emerald-400">"status": "OPERATIONAL"</p>
                     <p>{"}"}</p>
                  </div>
                </div>
              </div>

              <div className="bg-[#0f172aa6] border border-slate-800 rounded-2xl p-6">
                 <h3 className="text-lg font-bold text-white mb-6">Model Prediction Confidence Trend</h3>
                 <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      {renderSelectedChart(mockMetrics, "accuracy", "#f472b6", false)}
                    </ResponsiveContainer>
                 </div>
              </div>
            </div>
          )}

          {activeTab === 'system' && (
            <div className="bg-[#0f172aa6] border border-slate-800 rounded-2xl p-6 min-h-[60vh] flex flex-col items-center justify-center text-center">
               <Terminal className="w-16 h-16 text-slate-600 mb-6" />
               <h3 className="text-2xl font-bold text-white mb-2">Flask Core & Streamlit Architecture</h3>
               <p className="text-slate-400 max-w-lg mb-8">
                 The microservice architecture explicitly decouples the Streamlit UI from the XAI computation engine. System logs and tracebacks are clean.
               </p>
               <div className="inline-flex items-center gap-3 px-6 py-3 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full font-medium">
                 <span className="relative flex h-3 w-3">
                   <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                   <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                 </span>
                 All Systems Operating Nominal
               </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
