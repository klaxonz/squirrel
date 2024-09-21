import { useToast } from 'vue-toastification';

export default function useCustomToast() {
  const toast = useToast();

  const displayToast = (message, options = {}) => {
    toast(message, options);
  };

  return {
    displayToast,
  };
}