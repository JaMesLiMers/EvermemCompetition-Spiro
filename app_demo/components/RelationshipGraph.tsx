
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Person } from '../types';

interface RelationshipGraphProps {
  people: Person[];
  onSelectPerson: (id: string) => void;
  onEditPerson: (id: string) => void;
}

const RelationshipGraph: React.FC<RelationshipGraphProps> = ({ people, onSelectPerson, onEditPerson }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [menu, setMenu] = useState<{ x: number, y: number, personId: string } | null>(null);
  const [hoverInfo, setHoverInfo] = useState<{ x: number, y: number, text: string, name: string, count: number } | null>(null);

  useEffect(() => {
    if (!svgRef.current || people.length === 0) return;

    const width = window.innerWidth;
    const height = window.innerHeight;

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    svg.selectAll("*").remove();

    // Define Filters and Gradients
    const defs = svg.append('defs');
    
    // Glow Filter
    const filter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');
    filter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
    filter.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'blur').attr('operator', 'over');

    // Link Gradient
    const gradient = defs.append('linearGradient')
      .attr('id', 'link-gradient')
      .attr('gradientUnits', 'userSpaceOnUse');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', 'rgba(59, 130, 246, 0.1)');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', 'rgba(59, 130, 246, 0.8)');

    const container = svg.append('g').attr('class', 'container');

    // Zoom behavior with smooth transition
    const zoom = d3.zoom().scaleExtent([0.3, 3]).on('zoom', (event) => {
      container.attr('transform', event.transform);
      setMenu(null);
      setHoverInfo(null);
    });

    svg.call(zoom as any);

    const nodes = [
      { id: 'me', name: 'Me', type: 'author' },
      ...people.map(p => ({ ...p, type: 'person' }))
    ];

    const links = people.map(p => ({
      source: 'me',
      target: p.id,
      label: p.relationship,
      count: p.occurrenceCount
    }));

    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(220))
      .force('charge', d3.forceManyBody().strength(-2000))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(100));

    const linkGroup = container.append('g').attr('class', 'links');
    const nodeGroup = container.append('g').attr('class', 'nodes');

    // Curved Links (using path instead of line)
    const link = linkGroup.selectAll('path')
      .data(links)
      .enter().append('path')
      .attr('fill', 'none')
      .attr('stroke', 'rgba(255, 255, 255, 0.08)')
      .attr('stroke-width', d => Math.log(d.count + 1) * 2 + 1)
      .attr('class', 'transition-all duration-500 pointer-events-none')
      .attr('stroke-dasharray', '5, 5');

    const linkLabels = linkGroup.selectAll('g.link-label')
      .data(links)
      .enter().append('g')
      .attr('class', 'link-label opacity-0 transition-opacity duration-300 pointer-events-none');

    linkLabels.append('rect')
      .attr('fill', 'rgba(30, 58, 138, 0.8)')
      .attr('rx', 6)
      .attr('ry', 6);

    const linkText = linkLabels.append('text')
      .attr('fill', 'rgba(191, 219, 254, 1)')
      .attr('font-size', '10px')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-weight', 'bold')
      .text(d => d.label);

    linkText.each(function() {
      const bbox = (this as any).getBBox();
      d3.select((this as any).parentNode).select('rect')
        .attr('x', bbox.x - 6)
        .attr('y', bbox.y - 3)
        .attr('width', bbox.width + 12)
        .attr('height', bbox.height + 6);
    });

    const node = nodeGroup.selectAll('g.node')
      .data(nodes)
      .enter().append('g')
      .attr('class', 'node cursor-pointer transition-all duration-300')
      .call(d3.drag<SVGGElement, any>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended) as any)
      .on('click', (event, d: any) => {
        event.stopPropagation();
        if (d.type === 'person') {
          setMenu({ x: event.clientX, y: event.clientY, personId: d.id });
        }
      })
      .on('mouseenter', (event, d: any) => {
        if (d.id === 'me') return;
        
        setHoverInfo({
          x: event.clientX,
          y: event.clientY,
          name: d.name,
          text: d.relationship,
          count: d.occurrenceCount
        });

        // Interactive Highlight
        node.style('opacity', (n: any) => (n.id === d.id || n.id === 'me' ? 1 : 0.15))
            .style('filter', (n: any) => n.id === d.id ? 'url(#glow)' : 'none');
            
        link.style('stroke', (l: any) => (l.target.id === d.id ? 'rgba(59, 130, 246, 0.6)' : 'rgba(255, 255, 255, 0.02)'))
            .style('stroke-width', (l: any) => (l.target.id === d.id ? 5 : 1))
            .style('stroke-dasharray', (l: any) => (l.target.id === d.id ? 'none' : '5, 5'))
            .attr('filter', (l: any) => l.target.id === d.id ? 'url(#glow)' : 'none');

        linkLabels.style('opacity', (l: any) => (l.target.id === d.id ? 1 : 0));
        
        d3.select(event.currentTarget).select('circle.outer')
          .transition().duration(400)
          .attr('r', 55)
          .style('stroke', 'rgba(59, 130, 246, 1)');
      })
      .on('mouseleave', (event, d: any) => {
        setHoverInfo(null);
        node.style('opacity', 1).style('filter', 'none');
        link.style('stroke', 'rgba(255, 255, 255, 0.08)')
            .style('stroke-width', (l: any) => Math.log(l.count + 1) * 2 + 1)
            .style('stroke-dasharray', '5, 5')
            .attr('filter', 'none');
        linkLabels.style('opacity', 0);

        d3.select(event.currentTarget).select('circle.outer')
          .transition().duration(400)
          .attr('r', d.type === 'author' ? 52 : 42)
          .style('stroke', d.type === 'author' ? 'rgba(59, 130, 246, 0.4)' : 'rgba(255, 255, 255, 0.2)');
      });

    // Node layers for depth
    node.append('circle')
      .attr('class', 'pulse-ring')
      .attr('r', d => (d as any).type === 'author' ? 48 : 38)
      .attr('fill', 'none')
      .attr('stroke', 'rgba(59, 130, 246, 0.4)')
      .attr('stroke-width', 2)
      .style('opacity', 0);

    node.append('circle')
      .attr('class', 'outer')
      .attr('r', d => (d as any).type === 'author' ? 52 : 42)
      .attr('fill', 'rgba(0, 0, 0, 0.3)')
      .attr('stroke', d => (d as any).type === 'author' ? 'rgba(59, 130, 246, 0.4)' : 'rgba(255, 255, 255, 0.2)')
      .attr('stroke-width', 2);

    // Letter avatar: background circle
    const avatarColors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#6366F1', '#14B8A6'];
    function nameColor(name: string): string {
      let hash = 0;
      for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
      return avatarColors[Math.abs(hash) % avatarColors.length];
    }

    node.append('circle')
      .attr('class', 'avatar-bg')
      .attr('r', d => (d as any).type === 'author' ? 46 : 36)
      .attr('fill', (d: any) => nameColor(d.name));

    node.append('text')
      .attr('class', 'avatar-letter pointer-events-none')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', '#fff')
      .attr('font-size', d => (d as any).type === 'author' ? '36px' : '28px')
      .attr('font-weight', '700')
      .text((d: any) => d.name.charAt(0).toUpperCase());

    node.append('text')
      .text((d: any) => d.name)
      .attr('y', d => (d as any).type === 'author' ? 75 : 65)
      .attr('text-anchor', 'middle')
      .attr('fill', '#fff')
      .attr('font-size', '12px')
      .attr('font-weight', '600')
      .attr('class', 'pointer-events-none glow-text');

    // Continuous Pulse Animation for the Author Node
    const pulseAuthor = () => {
      node.filter((d: any) => d.type === 'author')
        .select('circle.pulse-ring')
        .attr('r', 48)
        .style('opacity', 0.8)
        .transition()
        .duration(2000)
        .ease(d3.easeLinear)
        .attr('r', 100)
        .style('opacity', 0)
        .on('end', pulseAuthor);
    };
    pulseAuthor();

    simulation.on('tick', () => {
      // Curved paths calculation
      link.attr('d', (d: any) => {
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.5; // Controls the curvature
        return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
      });

      linkLabels.attr('transform', (d: any) => {
        // Calculate midpoint of the arc for labels
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.5;
        
        // This is a rough approximation of the arc's midpoint
        const midX = (d.source.x + d.target.x) / 2 + (dy / dr) * (dr * 0.1);
        const midY = (d.source.y + d.target.y) / 2 - (dx / dr) * (dr * 0.1);
        return `translate(${midX}, ${midY})`;
      });

      node.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
    });

    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
      setMenu(null);
      setHoverInfo(null);
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    const handleClickOutside = () => setMenu(null);
    svg.on('click', handleClickOutside);

    // Initial Zoom to Fit
    svg.transition().duration(1500).call(
      zoom.transform as any,
      d3.zoomIdentity.translate(0, 0).scale(0.9)
    );

    return () => {
      svg.on('click', null);
      simulation.stop();
    };

  }, [people]);

  return (
    <div className="w-full h-full bg-black/95 flex items-center justify-center relative overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-blue-600/5 blur-[150px] rounded-full"></div>
        <div className="absolute top-0 left-0 w-full h-full bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-20 pointer-events-none"></div>
      </div>

      <svg ref={svgRef} className="w-full h-full relative z-10" />
      
      {/* Enhanced Relationship Tooltip */}
      {hoverInfo && (
        <div 
          className="fixed z-[160] pointer-events-none animate-tooltip-in"
          style={{ top: hoverInfo.y - 85, left: hoverInfo.x }}
        >
          <div className="bg-blue-900/40 backdrop-blur-2xl border border-blue-400/30 p-4 rounded-3xl shadow-[0_15px_40px_rgba(0,0,0,0.6)] -translate-x-1/2 min-w-[140px]">
            <div className="flex items-center justify-between mb-1 gap-4">
              <p className="text-[10px] text-blue-300 font-black uppercase tracking-[0.25em]">{hoverInfo.name}</p>
              <span className="bg-blue-500/20 text-blue-400 text-[9px] px-1.5 py-0.5 rounded-full font-bold">{hoverInfo.count} memories</span>
            </div>
            <p className="text-white text-xs font-light tracking-wide italic">“{hoverInfo.text}”</p>
          </div>
          {/* Arrow */}
          <div className="w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[8px] border-t-blue-400/30 mx-auto mt-[-1px]"></div>
        </div>
      )}

      {/* Node Action Menu */}
      {menu && (
        <div 
          className="fixed z-[150] bg-black/80 backdrop-blur-3xl border border-white/10 rounded-3xl p-3 shadow-[0_25px_60px_rgba(0,0,0,0.8)] animate-menu-in flex flex-col min-w-[180px]"
          style={{ top: menu.y + 20, left: menu.x - 90 }}
        >
          <div className="px-4 py-2 mb-2 border-b border-white/5">
            <p className="text-[10px] text-white/30 uppercase font-black tracking-widest">Actions</p>
          </div>
          <button 
            onClick={() => { onSelectPerson(menu.personId); setMenu(null); }}
            className="w-full text-left px-4 py-3 hover:bg-blue-600/20 hover:text-blue-200 rounded-2xl transition-all duration-300 text-sm flex items-center gap-4 text-white/80 group"
          >
            <span className="text-lg group-hover:scale-125 transition-transform">✨</span> Explore Spiro
          </button>
          <button 
            onClick={() => { onEditPerson(menu.personId); setMenu(null); }}
            className="w-full text-left px-4 py-3 hover:bg-white/10 rounded-2xl transition-all duration-300 text-sm flex items-center gap-4 text-white/80 group"
          >
            <span className="text-lg group-hover:scale-125 transition-transform">📝</span> Edit Profile
          </button>
        </div>
      )}

      <style>{`
        .animate-tooltip-in {
          animation: tooltipIn 0.4s cubic-bezier(0.17, 0.67, 0.83, 0.67) forwards;
        }
        .animate-menu-in {
          animation: menuIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes tooltipIn {
          from { opacity: 0; transform: translateY(10px) scale(0.95); filter: blur(4px); }
          to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
        }
        @keyframes menuIn {
          from { opacity: 0; transform: scale(0.8) translateY(-20px); filter: blur(8px); }
          to { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
        }
        .glow-text {
          text-shadow: 0 0 8px rgba(255, 255, 255, 0.4);
        }
      `}</style>
    </div>
  );
};

export default RelationshipGraph;
