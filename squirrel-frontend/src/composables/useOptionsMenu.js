import axios from '../utils/axios';

export default function useOptionsMenu(videoRef) {


  const copyVideoLink = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(videoRef.value.url)
        .catch(err => {
          fallbackCopyTextToClipboard(videoRef.value.url);
        });
    } else {
      fallbackCopyTextToClipboard(videoRef.value.url);
    }
  };

  const fallbackCopyTextToClipboard = (text) => {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('Fallback: Oops, unable to copy', err);
    }

    document.body.removeChild(textArea);
  };

  return {
    copyVideoLink,
  };
}
