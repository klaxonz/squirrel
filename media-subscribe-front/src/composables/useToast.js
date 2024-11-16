import { useToast } from 'vue-toastification';
import { h, render } from 'vue';

export default function useCustomToast() {
  const toast = useToast();

  const displayToast = (message, options = {}) => {
    toast(message, {
      position: "bottom-center",
      timeout: 3000,
      closeOnClick: true,
      pauseOnFocusLoss: true,
      pauseOnHover: true,
      draggable: false,
      showCloseButtonOnHover: false,
      hideProgressBar: true,
      closeButton: false,
      icon: false,
      rtl: false,
      className: 'youtube-toast',
      ...options
    });
  };

  const confirm = (message) => {
    return new Promise(resolve => {
      // 创建容器
      const container = document.createElement('div');
      container.className = 'fixed inset-0 bg-black/60 flex items-center justify-center z-50';
      document.body.appendChild(container);

      // 创建虚拟节点
      const vnode = h('div', {
        class: 'bg-[#282828] p-6 rounded-lg shadow-xl min-w-[400px] animate-fade-in'
      }, [
        h('div', { class: 'mb-6' }, [
          h('h3', { class: 'text-[16px] font-medium text-white mb-2' }, '确认取消订阅'),
          h('p', { class: 'text-[14px] text-[#aaaaaa]' }, message)
        ]),
        h('div', { class: 'flex justify-end items-center gap-3' }, [
          h('button', {
            class: `px-4 py-2 text-[14px] font-medium text-white hover:bg-[#3f3f3f] rounded-full 
                    transition-colors duration-200`,
            onClick: () => {
              document.body.removeChild(container);
              resolve(false);
            }
          }, '取消'),
          h('button', {
            class: `px-4 py-2 text-[14px] font-medium text-white bg-[#cc0000] hover:bg-[#990000] 
                    rounded-full transition-colors duration-200`,
            onClick: () => {
              document.body.removeChild(container);
              resolve(true);
            }
          }, '确认')
        ])
      ]);

      // 渲染到容器
      render(vnode, container);

      // 点击背景关闭
      container.addEventListener('click', (e) => {
        if (e.target === container) {
          document.body.removeChild(container);
          resolve(false);
        }
      });
    });
  };

  return {
    displayToast,
    confirm
  };
}
