import axios from "../utils/axios.js";


export default function useVideoInteraction() {

    const INTERACTION_TYPE = {
        LIKE: 1,
        DISLIKE: 2,
        LATER: 3,
    }

    const toggleLike = async (video_id, interaction_type) => {
        await axios.post('/api/video-interaction/toggle-like', {
            video_id: video_id,
            interaction_type: interaction_type
        });
    }

    const deleteInteraction = async (video_id, interaction_type) => {
        await axios.post('/api/video-interaction/delete', {
            video_id: video_id
        });
    }

    return {
        INTERACTION_TYPE,
        toggleLike,
        deleteInteraction
    }
}