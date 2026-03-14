
export interface AudioSnippet {
  sentenceIndex: number;
  audioUrl: string;
}

export interface Person {
  id: string;
  name: string;
  relationship: string;
  avatar?: string;
  occurrenceCount: number;
  diaryIds: string[];
}

export interface DiaryEntry {
  id: string;
  title: string;
  date: string;
  content: string;
  imageUrl?: string;
  audioSnippets?: AudioSnippet[];
  peopleIds: string[];
}

export interface Insight {
  id: string;
  text: string;
  type: 'birthday' | 'event' | 'personality' | 'promise' | 'need';
}

export interface LifeTopic {
  id: string;
  name: string;
  gravity: number; // 0-100, representing concern/intensity
  description: string;
  icon: string;
  color: string;
}

export interface AppState {
  currentDiary: DiaryEntry;
  diaries: DiaryEntry[];
  people: Person[];
  view: 'diary' | 'graph' | 'river' | 'home';
  selectedPersonId?: string;
  lifeTopics: LifeTopic[];
}
