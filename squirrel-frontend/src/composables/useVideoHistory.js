import axios from '../utils/axios';

export default function useVideoHistory() {

  const sendReport = async (video_id, currentTime) => {
    await axios.post('/api/video-history/update', {
      video_id:video_id,
      last_position: currentTime
    });
  };

  return {
    sendReport
  };
} 