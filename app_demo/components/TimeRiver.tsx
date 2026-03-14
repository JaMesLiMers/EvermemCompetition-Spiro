
import React, { useEffect, useRef, useState } from 'react';
import { DiaryEntry, Person, Insight } from '../types';

interface TimeRiverProps {
  person: Person;
  diaries: DiaryEntry[];
  insights: Insight[];
  onBack: () => void;
  onEdit: () => void;
}

const TimeRiver: React.FC<TimeRiverProps> = ({ person, diaries, insights, onBack, onEdit }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isInsightModalOpen, setIsInsightModalOpen] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    const particles: any[] = [];
    const particleCount = 800;
    let time = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = {
        x: (e.clientX - window.innerWidth / 2) / (window.innerWidth / 2),
        y: (e.clientY - window.innerHeight / 2) / (window.innerHeight / 2)
      };
    };
    window.addEventListener('mousemove', handleMouseMove);

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: (Math.random() - 0.5) * 2000,
        y: (Math.random() - 0.5) * 2000,
        z: Math.random() * 1000,
        speedZ: Math.random() * 1.5 + 0.5,
        baseX: (Math.random() - 0.5) * 2000,
        baseY: (Math.random() - 0.5) * 2000,
        color: `hsla(${190 + Math.random() * 70}, 80%, 75%, ${0.2 + Math.random() * 0.6})`,
        size: Math.random() * 2 + 0.5
      });
    }

    const draw = () => {
      time += 0.01;
      ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const cx = canvas.width / 2 + mouseRef.current.x * 50;
      const cy = canvas.height / 2 + mouseRef.current.y * 50;

      particles.forEach(p => {
        p.z -= p.speedZ;
        if (p.z <= 0) {
          p.z = 1000;
          p.x = p.baseX;
          p.y = p.baseY;
        }

        const flowFactor = Math.sin(p.z * 0.005 + time) * 100;
        const currentX = p.x + flowFactor;
        const currentY = p.y + Math.cos(p.z * 0.003 + time) * 50;

        const scale = 600 / p.z;
        const x2d = cx + currentX * scale;
        const y2d = cy + currentY * scale;
        
        const size = p.size * scale;
        const alpha = Math.min(1, (1000 - p.z) / 800);

        if (x2d > 0 && x2d < canvas.width && y2d > 0 && y2d < canvas.height) {
          ctx.beginPath();
          ctx.arc(x2d, y2d, size, 0, Math.PI * 2);
          ctx.fillStyle = p.color.replace(')', `, ${alpha})`);
          ctx.fill();

          if (p.z < 300) {
            ctx.shadowBlur = 10;
            ctx.shadowColor = p.color;
          } else {
            ctx.shadowBlur = 0;
          }
        }
      });

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, [person, diaries]);

  const personDiaries = diaries.filter(d => person.diaryIds.includes(d.id));

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black flex flex-col">
      <canvas ref={canvasRef} className="absolute inset-0 z-0" />
      
      <div ref={scrollContainerRef} className="relative z-10 flex flex-col items-center h-full p-8 galaxy-scroll overflow-y-auto pt-24 pb-64">
        
        {/* Top Controls */}
        <div className="fixed top-8 left-8 right-8 flex justify-between items-start z-[60]">
          <button 
            onClick={onBack}
            className="p-3 rounded-full bg-white/10 hover:bg-white/20 transition backdrop-blur-lg border border-white/10"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <div className="flex gap-4">
            <button 
              onClick={() => setIsInsightModalOpen(true)}
              className="p-3 rounded-full bg-blue-600/20 hover:bg-blue-600/40 transition backdrop-blur-lg border border-blue-400/30 relative group shadow-[0_0_20px_rgba(37,99,235,0.2)]"
            >
              <div className="absolute inset-0 rounded-full animate-ping bg-blue-400/10 group-hover:bg-blue-400/20" />
              <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              {insights.length > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 w-4">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-4 w-4 bg-blue-500 text-[8px] items-center justify-center font-bold">{insights.length}</span>
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Profile Header */}
        <div className="flex flex-col items-center mb-16 relative group">
          <div className="relative">
            <div
              className="w-32 h-32 rounded-full border-2 border-white/50 shadow-2xl mb-4 flex items-center justify-center text-white font-bold"
              style={{
                backgroundColor: (() => {
                  const colors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#6366F1', '#14B8A6'];
                  let hash = 0;
                  for (let i = 0; i < person.name.length; i++) hash = person.name.charCodeAt(i) + ((hash << 5) - hash);
                  return colors[Math.abs(hash) % colors.length];
                })(),
                fontSize: '3rem',
              }}
            >
              {person.name.charAt(0).toUpperCase()}
            </div>
          </div>
          <h2 className="text-3xl font-bold tracking-widest glow-text flex items-center gap-2">
            {person.name}
          </h2>
          <p className="text-white/60 mt-2 font-light tracking-tight">{person.relationship} · {person.occurrenceCount} shared moments</p>
        </div>

        {/* Memories List */}
        <div className="w-full max-w-2xl space-y-12 mb-12">
          {personDiaries.map((entry) => (
            <div 
              key={entry.id}
              className="relative p-8 rounded-[40px] bg-white/[0.03] border border-white/5 backdrop-blur-md hover:bg-white/[0.05] hover:border-white/10 transition transform hover:-translate-y-1 group"
            >
              <p className="text-[10px] text-blue-400 mb-3 uppercase font-bold tracking-widest opacity-60">{entry.date}</p>
              <h3 className="text-xl font-bold mb-4 tracking-tight">{entry.title}</h3>
              <p className="text-white/60 leading-relaxed text-sm font-light">
                {entry.content}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Insight Modal */}
      {isInsightModalOpen && (
        <div
          className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-xl flex items-center justify-center p-6 animate-pop-in"
          onClick={() => setIsInsightModalOpen(false)}
        >
          <div 
            className="w-full max-w-2xl bg-[#0d0d0f]/90 border border-blue-500/30 rounded-[48px] p-10 md:p-14 shadow-[0_0_100px_rgba(37,99,235,0.2)] relative overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Top Glowing Bar */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50" />
            
            <header className="flex justify-between items-center mb-10">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-blue-600/10 border border-blue-400/20 flex items-center justify-center shadow-inner">
                  <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse shadow-[0_0_15px_rgba(96,165,250,0.8)]" />
                </div>
                <div>
                  <h3 className="text-xl font-bold glow-text tracking-tight">Spiro · AI Insights</h3>
                  <p className="text-[10px] text-white/30 uppercase tracking-[0.3em] font-black mt-1">Deep Context Retrieval</p>
                </div>
              </div>
              <button
                onClick={() => setIsInsightModalOpen(false)}
                className="p-3 hover:bg-white/5 rounded-full transition-all group"
              >
                <svg className="w-6 h-6 text-white/40 group-hover:text-white group-hover:rotate-90 transition-all duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </header>

            <div className="galaxy-scroll max-h-[50vh] overflow-y-auto pr-6 space-y-8">
              <div className="space-y-6">
                {insights.map((insight, idx) => (
                    <div 
                      key={insight.id} 
                      className="p-6 rounded-3xl bg-white/[0.02] border border-white/5 hover:border-blue-400/20 transition-all group animate-fade-in"
                      style={{ animationDelay: `${idx * 150}ms` }}
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <span className={`w-2 h-2 rounded-full ${insight.type === 'promise' ? 'bg-amber-400' : 'bg-blue-400'}`} />
                        <span className="text-[10px] text-white/40 uppercase font-black tracking-widest">{insight.type}</span>
                      </div>
                      <p className="text-white/80 font-light leading-relaxed">
                        {insight.text}
                      </p>
                    </div>
                  ))}
                  {insights.length === 0 && (
                    <p className="text-white/20 italic text-center py-12">No deeper insights found yet...</p>
                  )}
                </div>
            </div>

            <footer className="mt-12 pt-8 border-t border-white/5 flex flex-col items-center">
               <p className="text-[10px] text-white/20 italic tracking-[0.4em] uppercase font-bold">Processed via Spiro Engine</p>
            </footer>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pop-in {
          from { opacity: 0; transform: scale(0.9) translateY(40px); filter: blur(20px); }
          to { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
        }
        .animate-pop-in {
          animation: pop-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .animate-fade-in {
          animation: fadeIn 0.8s ease-out forwards;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default TimeRiver;
