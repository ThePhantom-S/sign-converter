import React, { useEffect } from 'react';
import { Save, Settings, Database, Sliders, Globe, Sparkles } from 'lucide-react';
import { useSettingsStore } from '../store/settingsStore';

const App: React.FC = () => {
  const settings = useSettingsStore();

  useEffect(() => {
    settings.loadSettings();
  }, []);

  const handleSave = () => {
    // Show quick notification or alert
    alert('Settings synced successfully!');
  };

  if (!settings.isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950 text-slate-400">
        <p className="animate-pulse">Loading configurations...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center py-12 px-4 font-sans select-none">
      <div className="w-full max-w-2xl space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-sky-500/10 text-sky-400 rounded-xl border border-sky-500/20">
              <Settings className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">SignBridge Live</h1>
              <p className="text-xs text-slate-400">Configure real-time translation, captions layout, and sign language models</p>
            </div>
          </div>

          <button 
            onClick={handleSave}
            className="flex items-center gap-2 bg-sky-500 hover:bg-sky-400 text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-lg shadow-sky-500/20 transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Panel 1: Transcription Engine */}
          <div className="bg-slate-900/60 border border-white/5 rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-semibold flex items-center gap-2 text-white/95">
              <Globe className="w-4 h-4 text-sky-400" />
              <span>Language & Processing</span>
            </h2>
            
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] text-slate-400 font-semibold mb-1.5 uppercase tracking-wider">Spoken Language</label>
                <select 
                  value={settings.language}
                  onChange={(e) => settings.setSetting('language', e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 text-slate-200 text-xs rounded-lg p-2.5 outline-none focus:border-sky-500 transition-colors"
                >
                  <option value="en-US">English (United States)</option>
                  <option value="es-ES">Spanish (Spain)</option>
                  <option value="fr-FR">French (France)</option>
                  <option value="de-DE">German (Germany)</option>
                  <option value="ja-JP">Japanese (Japan)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 font-semibold mb-1.5 uppercase tracking-wider">Recognition Mode</label>
                <div className="grid grid-cols-2 gap-2">
                  <button 
                    onClick={() => settings.setSetting('recognitionMode', 'speech-api')}
                    className={`p-2.5 rounded-lg border text-xs font-semibold text-center transition-all ${
                      settings.recognitionMode === 'speech-api'
                        ? 'bg-sky-500/10 border-sky-500 text-sky-400'
                        : 'bg-slate-950 border-white/5 text-slate-400 hover:border-white/10'
                    }`}
                  >
                    Speech API (Local)
                  </button>
                  <button 
                    onClick={() => settings.setSetting('recognitionMode', 'backend-ai')}
                    className={`p-2.5 rounded-lg border text-xs font-semibold text-center transition-all ${
                      settings.recognitionMode === 'backend-ai'
                        ? 'bg-sky-500/10 border-sky-500 text-sky-400'
                        : 'bg-slate-950 border-white/5 text-slate-400 hover:border-white/10'
                    }`}
                  >
                    Backend AI (FastAPI)
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Panel 2: Visual Caption Settings */}
          <div className="bg-slate-900/60 border border-white/5 rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-semibold flex items-center gap-2 text-white/95">
              <Sliders className="w-4 h-4 text-sky-400" />
              <span>Caption Aesthetics</span>
            </h2>
            
            <div className="space-y-3.5">
              <div>
                <label className="block text-[11px] text-slate-400 font-semibold mb-1.5 uppercase tracking-wider">Font Size</label>
                <select 
                  value={settings.captionSize}
                  onChange={(e) => settings.setSetting('captionSize', e.target.value as any)}
                  className="w-full bg-slate-950 border border-white/10 text-slate-200 text-xs rounded-lg p-2.5 outline-none focus:border-sky-500 transition-colors"
                >
                  <option value="small">Small (14px)</option>
                  <option value="medium">Medium (16px)</option>
                  <option value="large">Large (18px)</option>
                  <option value="huge">Huge (22px)</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between mb-1.5">
                  <label className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Transparency</label>
                  <span className="text-xs text-sky-400 font-semibold">{settings.transparency}%</span>
                </div>
                <input 
                  type="range" 
                  min="30" 
                  max="100" 
                  value={settings.transparency} 
                  onChange={(e) => settings.setSetting('transparency', parseInt(e.target.value))}
                  className="w-full accent-sky-500 cursor-pointer bg-slate-950 h-1.5 rounded-lg appearance-none"
                />
              </div>
            </div>
          </div>

          {/* Panel 3: Server Configurations */}
          <div className="bg-slate-900/60 border border-white/5 rounded-2xl p-5 space-y-4 md:col-span-2">
            <h2 className="text-sm font-semibold flex items-center gap-2 text-white/95">
              <Database className="w-4 h-4 text-sky-400" />
              <span>FastAPI Backend Connection</span>
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] text-slate-400 font-semibold mb-1.5 uppercase tracking-wider">Server Endpoint URL</label>
                <input 
                  type="url" 
                  value={settings.backendUrl} 
                  onChange={(e) => settings.setSetting('backendUrl', e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 text-slate-200 text-xs rounded-lg p-2.5 outline-none focus:border-sky-500 transition-colors"
                  placeholder="http://localhost:8000"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 font-semibold mb-1.5 uppercase tracking-wider">API Authentication Key</label>
                <input 
                  type="password" 
                  value={settings.apiKey} 
                  onChange={(e) => settings.setSetting('apiKey', e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 text-slate-200 text-xs rounded-lg p-2.5 outline-none focus:border-sky-500 transition-colors"
                  placeholder="Bearer token or API Secret key"
                />
              </div>
            </div>
          </div>

          {/* Panel 4: Avatar Engine */}
          <div className="bg-slate-900/60 border border-white/5 rounded-2xl p-5 space-y-4 md:col-span-2">
            <h2 className="text-sm font-semibold flex items-center gap-2 text-white/95">
              <Sparkles className="w-4 h-4 text-sky-400" />
              <span>Sign Language Avatar Model</span>
            </h2>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[
                { id: 'default-3d-signbot', name: '3D SignBot Standard', type: 'Mesh' },
                { id: 'photorealistic-avatar', name: 'Photorealistic Render', type: 'Neural Model' },
                { id: 'minimal-vector-avatar', name: '2D Flat Outline Vector', type: 'Vector' }
              ].map((av) => (
                <button
                  key={av.id}
                  onClick={() => settings.setSetting('avatar', av.id)}
                  className={`p-4 rounded-xl border text-left flex flex-col justify-between h-28 transition-all ${
                    settings.avatar === av.id
                      ? 'bg-sky-500/10 border-sky-500 text-white shadow-lg shadow-sky-500/5'
                      : 'bg-slate-950 border-white/5 text-slate-400 hover:border-white/10'
                  }`}
                >
                  <span className="text-[10px] text-sky-400 font-bold uppercase tracking-wider">{av.type}</span>
                  <span className="text-xs font-semibold mt-auto">{av.name}</span>
                </button>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};

export default App;
