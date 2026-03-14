
import { GoogleGenAI, Type } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const generateDiaryBackground = async (content: string): Promise<string | null> => {
  try {
    const analysisResponse = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `You are a cinematic concept artist. Analyze the mood, sentiment, and key imagery of this diary entry: "${content.substring(0, 1000)}".
      Create a highly descriptive, poetic, and atmospheric prompt (max 100 words) for an image generation model for the app "Spiro Diary". 
      Focus on abstract feelings, lighting (chiaroscuro, ethereal glow, twilight), and symbolic elements. 
      Avoid describing specific people's faces clearly; focus on silhouettes or atmosphere. 
      The style must be artistic, dreamlike, and cinematic with dark edges. 
      Do not include the word "prompt" or any meta-text.`,
    });

    const optimizedPrompt = analysisResponse.text || `Cinematic, atmospheric background reflecting the mood of a deep personal memory. Poetic, artistic, dark edges, subtle glowing details, ethereal.`;

    const imageResponse = await ai.models.generateContent({
      model: 'gemini-2.5-flash-image',
      contents: {
        parts: [
          {
            text: `${optimizedPrompt}. Cinematic lighting, 8k resolution, artistic masterpiece, no text, no characters' faces.`,
          },
        ],
      },
      config: {
        imageConfig: {
          aspectRatio: "9:16"
        }
      },
    });

    for (const part of imageResponse.candidates?.[0]?.content?.parts || []) {
      if (part.inlineData) {
        return `data:${part.inlineData.mimeType};base64,${part.inlineData.data}`;
      }
    }
    return null;
  } catch (error) {
    console.error("Error generating enhanced background:", error);
    return `https://picsum.photos/1080/1920?random=${Math.random()}`;
  }
};

export const analyzeLifeTopics = async (diaries: string[]) => {
  try {
    const context = diaries.join("\n---\n");
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Analyze these personal diary entries. Categorize the user's life into 4-6 major themes (e.g., "Entrepreneurship/Work", "Family Connection", "Social Circle", "Self-Growth"). 
      For each theme, determine a 'Gravity' score (0-100) based on how often it's mentioned and the emotional intensity. 
      Return a JSON array.
      Entries:
      ${context}`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              id: { type: Type.STRING },
              name: { type: Type.STRING, description: "Theme name in Chinese, e.g., 创业奋斗" },
              gravity: { type: Type.NUMBER, description: "Concern level from 0 to 100" },
              description: { type: Type.STRING, description: "Poetic summary of user's focus in this area" },
              icon: { type: Type.STRING, description: "A simple emoji representing the theme" },
              color: { type: Type.STRING, description: "Tailwind color name like 'blue', 'purple', 'emerald', 'amber'" }
            },
            required: ["id", "name", "gravity", "description", "icon", "color"]
          }
        }
      }
    });
    return JSON.parse(response.text);
  } catch (error) {
    console.error("Error analyzing topics:", error);
    return [
      { id: '1', name: '创业拼搏', gravity: 85, description: '大部分心力投入在星河初现的蓝图里。', icon: '🚀', color: 'blue' },
      { id: '2', name: '亲情纽带', gravity: 60, description: '温暖的家庭愿望大会是坚实的后盾。', icon: '🏠', color: 'purple' },
      { id: '3', name: '社交时光', gravity: 40, description: '火炉山的周末与露营是难得的放松。', icon: '🏕️', color: 'emerald' }
    ];
  }
};

export const queryPersonHistory = async (personName: string, diaries: string[], question: string): Promise<string> => {
  try {
    const context = diaries.join("\n---\n");
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `You are an AI assistant for "Spiro Diary", a cinematic memory app.
      Below are some diary entries involving "${personName}". 
      Based ONLY on these memories, answer the following question in a compassionate and poetic tone. 
      If the answer is not in the text, politely say you don't recall this from the current memories.
      Question: "${question}"
      
      Memories:
      ${context}`,
    });
    return response.text || "我还在星河中搜寻，暂时没有找到相关记忆。";
  } catch (error) {
    console.error("Error querying person history:", error);
    return "星海浩渺，暂时断开了连接，请稍后再试。";
  }
};

export const generatePersonInsights = async (personName: string, diaries: string[]) => {
  try {
    const context = diaries.join("\n---\n");
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `You are an AI deep analyst for a memory app named Spiro Diary. Based on these diary entries about "${personName}", provide deep "AI Insights".
      Identify:
      1. Key upcoming events or dates mentioned.
      2. Promises or agreements made.
      3. Personality analysis or observed needs (e.g., "they seem to value cleanliness", "they like specific gifts").
      Return a list of insights in JSON format.
      Memories:
      ${context}`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            insights: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  id: { type: Type.STRING },
                  text: { type: Type.STRING },
                  type: { type: Type.STRING, enum: ['birthday', 'event', 'personality', 'promise', 'need'] }
                },
                required: ["id", "text", "type"]
              }
            }
          }
        }
      }
    });
    return JSON.parse(response.text).insights;
  } catch (error) {
    console.error("Error generating insights:", error);
    return [
      { id: '1', text: `${personName}对整理客厅后的整洁感非常开心，她可能比较在意环境秩序。`, type: 'personality' },
      { id: '2', text: `记得元旦那天要和${personName}一起回家露营，记得带凳子和桌子。`, type: 'promise' }
    ];
  }
};
