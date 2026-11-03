export interface ResettableServices<T> {
  current(): T;
  reset<R>(dropCollection: () => Promise<R>): Promise<R>;
}

/** Rebuilds provider objects after their backing demo tables are dropped. */
export function createResettableServices<T>(create: () => T): ResettableServices<T> {
  let services = create();
  return {
    current: () => services,
    async reset(dropCollection) {
      const result = await dropCollection();
      services = create();
      return result;
    },
  };
}
