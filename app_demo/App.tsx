
import React, { useState, useRef } from 'react';
import { DiaryEntry, Person, AppState, LifeTopic, Insight } from './types';
import ParticleEdges from './components/ParticleEdges';
import RelationshipGraph from './components/RelationshipGraph';
import TimeRiver from './components/TimeRiver';
import EditPersonModal from './components/EditPersonModal';

import peopleData from './data/people.json';
import diariesData from './data/diaries.json';
import lifeTopicsData from './data/life-topics.json';
import insightsData from './data/insights.json';

const App: React.FC = () => {
  const [state, setState] = useState<AppState>({
    currentDiary: diariesData[0] as DiaryEntry,
    diaries: diariesData as DiaryEntry[],
    people: peopleData as Person[],
    view: 'home',
    lifeTopics: lifeTopicsData as LifeTopic[],
  });

  const [scrollY, setScrollY] = useState(0);
  const [editingPersonId, setEditingPersonId] = useState<string | null>(null);
  const [showParticipants, setShowParticipants] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    setScrollY(e.currentTarget.scrollTop);
  };

  const handleSwitchDiary = (diary: DiaryEntry) => {
    setState(prev => ({ ...prev, currentDiary: diary, view: 'diary' }));
    setShowParticipants(false);
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleUpdatePerson = (updatedPerson: Person) => {
    setState(prev => ({
      ...prev,
      people: prev.people.map(p => p.id === updatedPerson.id ? updatedPerson : p)
    }));
    setEditingPersonId(null);
  };

  const sentences = state.currentDiary.content.split('\n').filter(s => s.trim() !== '');
  const bgOpacity = Math.max(0.1, 1 - scrollY / window.innerHeight);
  const currentParticipants = state.people.filter(p => state.currentDiary.peopleIds.includes(p.id));

  // Letter avatar helper
  const avatarColors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#6366F1', '#14B8A6'];
  const nameColor = (name: string) => {
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return avatarColors[Math.abs(hash) % avatarColors.length];
  };

  const renderAvatar = (person: Person, size: number = 48) => (
    <div
      className="rounded-full flex items-center justify-center text-white font-bold"
      style={{
        width: size, height: size,
        backgroundColor: nameColor(person.name),
        fontSize: size * 0.4,
      }}
    >
      {person.name.charAt(0).toUpperCase()}
    </div>
  );

  const renderHomeView = () => (
    <div className="relative w-full h-full overflow-y-auto galaxy-scroll p-8 md:p-16 animate-fade-in">
      <div className="max-w-6xl mx-auto pt-12">
        <header className="flex justify-between items-start mb-16">
          <div>
            <h1 className="text-5xl font-bold glow-text tracking-tighter mb-4">Spiro</h1>
            <p className="text-white/40 tracking-widest uppercase text-xs">The Gallery of Your Forgotten Stars</p>
          </div>
          <div className="flex items-center gap-6">
            <button
              onClick={() => setState(prev => ({ ...prev, view: 'graph' }))}
              className="px-6 py-3 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-all backdrop-blur-md flex items-center gap-3 group"
            >
              <div className="w-5 h-5 group-hover:scale-110 transition-transform">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full text-blue-400">
                  <circle cx="12" cy="12" r="2" fill="currentColor"/>
                  <circle cx="6" cy="7" r="1.5"/>
                  <circle cx="18" cy="6" r="1.5"/>
                  <circle cx="5" cy="17" r="1.5"/>
                  <circle cx="17" cy="18" r="1.5"/>
                </svg>
              </div>
              <span className="text-[10px] text-white/50 font-bold uppercase tracking-widest">Spiro Map</span>
            </button>
          </div>
        </header>

        {/* Spiro Nebula: Life Topic Analysis */}
        <section className="mb-24">
          <div className="flex items-center gap-4 mb-8">
            <h2 className="text-xs font-bold text-white/30 uppercase tracking-[0.4em]">Spiro Nebula · Life Topics</h2>
            <div className="h-[1px] flex-1 bg-white/10" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {state.lifeTopics.length > 0 ? state.lifeTopics.map(topic => (
              <div key={topic.id} className="relative group p-6 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/5 transition-all overflow-hidden">
                <div
                  className="absolute -top-12 -right-12 w-32 h-32 rounded-full blur-[40px] opacity-20 transition-opacity group-hover:opacity-40"
                  style={{ backgroundColor: topic.color === 'blue' ? '#3b82f6' : topic.color === 'purple' ? '#a855f7' : topic.color === 'emerald' ? '#10b981' : '#f59e0b' }}
                />
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-2xl">{topic.icon}</span>
                    <span className="text-[10px] font-black text-blue-400/60">{topic.gravity}G</span>
                  </div>
                  <h3 className="text-sm font-bold text-white mb-2">{topic.name}</h3>
                  <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden mb-3">
                    <div
                      className="h-full rounded-full transition-all duration-1000"
                      style={{
                        width: `${topic.gravity}%`,
                        backgroundColor: topic.color === 'blue' ? '#3b82f6' : topic.color === 'purple' ? '#a855f7' : topic.color === 'emerald' ? '#10b981' : '#f59e0b'
                      }}
                    />
                  </div>
                  <p className="text-[10px] text-white/40 leading-relaxed italic line-clamp-2">{topic.description}</p>
                </div>
              </div>
            )) : (
              <div className="col-span-full text-center py-12 text-white/20 text-sm italic">
                No life topics analyzed yet. Re-run the profiling task with new prompts.
              </div>
            )}
          </div>
        </section>

        <div className="flex items-center gap-4 mb-8">
          <h2 className="text-xs font-bold text-white/30 uppercase tracking-[0.4em]">Memory Fragments</h2>
          <div className="h-[1px] flex-1 bg-white/10" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {state.diaries.map(diary => (
            <div
              key={diary.id}
              onClick={() => handleSwitchDiary(diary)}
              className="group relative h-80 rounded-[40px] overflow-hidden cursor-pointer border border-white/5 hover:border-white/20 transition-all transform hover:-translate-y-2"
            >
              {diary.imageUrl ? (
                <img src={diary.imageUrl} className="absolute inset-0 w-full h-full object-cover transition duration-1000 group-hover:scale-110 opacity-40 group-hover:opacity-70 grayscale group-hover:grayscale-0" />
              ) : (
                <div className="absolute inset-0 bg-gradient-to-br from-blue-900/30 to-purple-900/30" />
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-8">
                <p className="text-[10px] text-blue-500 font-bold uppercase tracking-widest mb-2 opacity-60 group-hover:opacity-100 transition">{diary.date}</p>
                <h3 className="text-xl font-bold group-hover:text-blue-100 transition leading-tight">{diary.title}</h3>
                <p className="text-white/40 text-xs mt-3 line-clamp-2 leading-relaxed font-light group-hover:text-white/60 transition">{diary.content}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderDiaryView = () => (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="relative w-full h-full overflow-y-auto galaxy-scroll scroll-smooth"
    >
      <div
        className="fixed inset-0 z-0 bg-cover bg-center transition-all duration-700 ease-out"
        style={{
          backgroundImage: state.currentDiary.imageUrl ? `url(${state.currentDiary.imageUrl})` : undefined,
          backgroundColor: state.currentDiary.imageUrl ? undefined : '#0a0a0f',
          opacity: bgOpacity,
          transform: `scale(${1 + scrollY / 2000})`,
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black/30" />
      </div>

      <ParticleEdges />

      <div className="fixed top-8 left-8 z-50">
        <button
          onClick={() => setState(prev => ({ ...prev, view: 'home' }))}
          className="p-4 rounded-full bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
        </button>
      </div>

      <div className="fixed top-8 right-8 z-50 flex flex-col items-center gap-4">
        <div className="flex flex-col items-center gap-4">
          {currentParticipants.length === 1 ? (
            <button
              onClick={() => setState(prev => ({ ...prev, selectedPersonId: currentParticipants[0].id, view: 'river' }))}
              className="group relative z-50 p-0.5 rounded-full border-2 border-white/20 hover:border-blue-400 transition-all shadow-lg active:scale-95"
            >
              {renderAvatar(currentParticipants[0], 48)}
              <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 px-2 py-1 bg-black/60 backdrop-blur-md border border-white/10 rounded-md text-[10px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                {currentParticipants[0].name}
              </div>
            </button>
          ) : currentParticipants.length > 1 ? (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); setShowParticipants(!showParticipants); }}
                className={`p-4 rounded-full bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition relative z-50 ${showParticipants ? 'bg-white/30 border-blue-400/50' : ''}`}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <span className="absolute -bottom-1 -right-1 bg-blue-500 text-[10px] font-bold px-1.5 py-0.5 rounded-full ring-2 ring-black">
                  {currentParticipants.length}
                </span>
              </button>

              <div className={`flex flex-col gap-3 transition-all duration-500 ease-out overflow-hidden z-40 ${showParticipants ? 'max-h-[500px] opacity-100 mt-2' : 'max-h-0 opacity-0'}`}>
                {currentParticipants.map((person) => (
                  <button
                    key={person.id}
                    onClick={() => setState(prev => ({ ...prev, selectedPersonId: person.id, view: 'river' }))}
                    className="group relative p-0.5 rounded-full border-2 border-white/10 hover:border-blue-400 transition-all shadow-md"
                  >
                    {renderAvatar(person, 40)}
                    <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 px-2 py-1 bg-black/60 backdrop-blur-md border border-white/10 rounded-md text-[10px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      {person.name}
                    </div>
                  </button>
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>

      <div className="relative z-30 pt-[50vh] min-h-[150vh] px-8 pb-32">
        <div className="max-w-2xl mx-auto transition-transform duration-500" style={{ transform: `translateY(${Math.min(0, -scrollY * 0.2)}px)` }}>
          <div className="mb-12">
            <span className="text-sm font-light tracking-widest text-white/50 mb-2 block uppercase">{state.currentDiary.date}</span>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-8 glow-text leading-tight">{state.currentDiary.title}</h1>
          </div>

          <div className="space-y-12 text-lg md:text-xl font-light leading-relaxed text-white/90 mb-24">
            {sentences.map((sentence, idx) => (
              <p key={idx}>{sentence}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="w-screen h-screen overflow-hidden bg-black select-none">
      {state.view === 'home' && renderHomeView()}
      {state.view === 'diary' && renderDiaryView()}
      {state.view === 'graph' && (
        <div className="fixed inset-0 z-[100] bg-black flex flex-col">
          <div className="p-8 flex justify-between items-center bg-black/50 backdrop-blur-md z-[110]">
            <h2 className="text-2xl font-bold tracking-widest glow-text">Spiro Map</h2>
            <button
              onClick={() => setState(prev => ({ ...prev, view: 'home' }))}
              className="px-6 py-2 rounded-full border border-white/20 hover:bg-white/10 transition"
            >
              Home
            </button>
          </div>
          <RelationshipGraph
            people={state.people}
            onSelectPerson={(id) => setState(prev => ({ ...prev, selectedPersonId: id, view: 'river' }))}
            onEditPerson={(id) => setEditingPersonId(id)}
          />
        </div>
      )}
      {state.view === 'river' && state.selectedPersonId && (
        <TimeRiver
          person={state.people.find(p => p.id === state.selectedPersonId)!}
          diaries={state.diaries}
          insights={(insightsData as Record<string, Insight[]>)[state.selectedPersonId] || []}
          onBack={() => setState(prev => ({ ...prev, view: 'graph' }))}
          onEdit={() => setEditingPersonId(state.selectedPersonId!)}
        />
      )}
      {editingPersonId && (
        <EditPersonModal
          person={state.people.find(p => p.id === editingPersonId)!}
          onSave={handleUpdatePerson}
          onClose={() => setEditingPersonId(null)}
        />
      )}
      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fade-in {
          animation: fade-in 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  );
};

export default App;
