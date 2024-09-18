import { ref } from 'vue';

export default function useToast() {
  const toastMessage = ref('');
  const showToast = ref(false);

  const displayToast = (message, duration = 3000) => {
    toastMessage.value = message;
    showToast.value = true;
    setTimeout(() => {
      showToast.value = false;
    }, duration);
  };

  return {
    toastMessage,
    showToast,
    displayToast,
  };
}