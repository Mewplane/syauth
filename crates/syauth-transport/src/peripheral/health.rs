//! Latch controller removal even when BlueZ reuses the same adapter name.

use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

use futures::{Stream, StreamExt};

pub(super) struct AdapterLifetime {
    lost: Arc<AtomicBool>,
    task: tokio::task::JoinHandle<()>,
}
impl AdapterLifetime {
    pub(super) fn watch(events: impl Stream<Item = bluer::SessionEvent> + Send + 'static, name: String) -> Self {
        let lost = Arc::new(AtomicBool::new(false));
        let flag = lost.clone();
        let task = tokio::spawn(async move {
            futures::pin_mut!(events);
            while let Some(event) = events.next().await {
                if event == bluer::SessionEvent::AdapterRemoved(name.clone()) {
                    break;
                }
            }
            flag.store(true, Ordering::Release);
        });
        Self { lost, task }
    }
    pub(super) fn is_lost(&self) -> bool {
        self.lost.load(Ordering::Acquire)
    }
}
impl Drop for AdapterLifetime {
    fn drop(&mut self) {
        self.task.abort();
    }
}

#[cfg(test)]
mod tests {
    use futures::channel::mpsc;

    use super::*;

    #[tokio::test]
    async fn unrelated_controller_removal_keeps_transport_live() {
        let (tx, rx) = mpsc::unbounded();
        let lifetime = AdapterLifetime::watch(rx, "hci1".into());
        tx.unbounded_send(bluer::SessionEvent::AdapterRemoved("hci0".into()))
            .expect("remove");
        tokio::task::yield_now().await;
        assert!(!lifetime.is_lost());
    }

    #[tokio::test]
    async fn closed_controller_event_stream_invalidates_transport() {
        let lifetime = AdapterLifetime::watch(futures::stream::empty(), "hci0".into());
        tokio::task::yield_now().await;
        assert!(lifetime.is_lost());
    }

    #[tokio::test]
    async fn removed_controller_stays_invalid_after_same_name_returns() {
        let (tx, rx) = mpsc::unbounded();
        let lifetime = AdapterLifetime::watch(rx, "hci0".into());
        tx.unbounded_send(bluer::SessionEvent::AdapterRemoved("hci0".into()))
            .expect("remove");
        tx.unbounded_send(bluer::SessionEvent::AdapterAdded("hci0".into()))
            .expect("replace");
        tokio::task::yield_now().await;
        assert!(lifetime.is_lost());
    }
}
