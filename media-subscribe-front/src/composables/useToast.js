import { useToast } from 'vue-toastification';

export default function useCustomToast() {
  const toast = useToast();

  const displayToast = (message, options = {}) => {
    toast(message, {
      ...options,
      position: "top-center",
      hideProgressBar: true,
      closeButton: false,
      timeout: 2000
    });
  };

  return {
    displayToast,
  };
}