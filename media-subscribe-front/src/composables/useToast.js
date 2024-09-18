import { ref } from 'vue';

const toastMessage = ref('');
const showToast = ref(false);

export default function useToast() {
  const displayToast = (message, duration = 3000) => {
    console.log('displayToast', message);
    showToast.value = true;
    toastMessage.value = message;
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