import { useToast } from 'vue-toastification';

export default function useCustomToast() {
  const toast = useToast();

  const displayToast = (message, options = {}) => {
    toast(message, {
      position: "top-center",
      timeout: 2000,
      closeOnClick: true,
      pauseOnFocusLoss: true,
      pauseOnHover: true,
      draggable: true,
      draggablePercent: 0.6,
      showCloseButtonOnHover: false,
      hideProgressBar: true,
      closeButton: false,
      icon: true,
      rtl: false,
      ...options
    });
  };

  return {
    displayToast,
  };
}
