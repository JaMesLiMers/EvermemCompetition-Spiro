
import React, { useState } from 'react';
import { Person } from '../types';

interface EditPersonModalProps {
  person: Person;
  onSave: (updatedPerson: Person) => void;
  onClose: () => void;
}

const EditPersonModal: React.FC<EditPersonModalProps> = ({ person, onSave, onClose }) => {
  const [name, setName] = useState(person.name);
  const [relationship, setRelationship] = useState(person.relationship);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...person,
      name,
      relationship,
    });
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-white/5 border border-white/10 backdrop-blur-2xl rounded-3xl p-8 shadow-2xl ring-1 ring-white/20">
        <h3 className="text-2xl font-bold mb-6 glow-text tracking-widest text-center">Edit Profile</h3>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex justify-center mb-6">
            <div className="relative group">
              <div
                className="w-24 h-24 rounded-full border-2 border-blue-400/50 shadow-[0_0_20px_rgba(59,130,246,0.3)] flex items-center justify-center text-white font-bold text-3xl"
                style={{
                  backgroundColor: (() => {
                    const colors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#6366F1', '#14B8A6'];
                    let hash = 0;
                    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
                    return colors[Math.abs(hash) % colors.length];
                  })(),
                }}
              >
                {name.charAt(0).toUpperCase()}
              </div>
              <div className="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-[10px] uppercase tracking-tighter">
                Preview
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-white/40 uppercase tracking-widest mb-2 ml-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
              placeholder="Enter name"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-white/40 uppercase tracking-widest mb-2 ml-1">Relationship</label>
            <input
              type="text"
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
              placeholder="e.g. Mother, Friend, Colleague"
              required
            />
          </div>

          <div className="flex gap-4 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 rounded-xl border border-white/10 hover:bg-white/5 transition font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 transition font-bold shadow-lg shadow-blue-600/20"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditPersonModal;
